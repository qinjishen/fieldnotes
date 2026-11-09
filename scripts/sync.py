#!/usr/bin/env python3
"""Prepare a coherent snapshot; mark it published only after native Sites success."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from publishing import fingerprint
STATE=ROOT/'.publish-state'
STATE.mkdir(exist_ok=True)

def read(name):
    p=STATE/name
    return json.loads(p.read_text()) if p.exists() else {}

def save(name,data):
    tmp=STATE/(name+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(STATE/name)

def output_hash(folder=None):
    folder=folder or ROOT/'dist'
    h=hashlib.sha256()
    for p in sorted(folder.rglob('*')):
        if p.is_file(): h.update(p.relative_to(folder).as_posix().encode());h.update(p.read_bytes())
    return h.hexdigest()

def prepare(preview=False):
    before=fingerprint(ROOT)
    temp=Path(tempfile.mkdtemp(prefix='.build-',dir=ROOT))
    try:
        result=subprocess.run([sys.executable,str(ROOT/'build.py')],env={**os.environ,'FIELDNOTES_OUTPUT':str(temp),'FIELDNOTES_PREVIEW':'1' if preview else '0'},capture_output=True,text=True,cwd=ROOT)
        if result.returncode: raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        report=json.loads(result.stdout.strip().splitlines()[-1])
        if fingerprint(ROOT)!=before: raise RuntimeError('文档仍在变化，本次未生成发布快照，请等文件保存完后重试。')
        (temp/'build-info.json').write_text(json.dumps({'articles':report['articles'],'fingerprint':before}))
        target=STATE/'preview' if preview else ROOT/'dist'
        old=ROOT/('.build-previous-preview' if preview else '.build-previous')
        if old.exists(): shutil.rmtree(old)
        if target.exists(): target.rename(old)
        temp.rename(target)
        if old.exists(): shutil.rmtree(old)
        data={'fingerprint':before,'output_hash':output_hash(target),'built_at':datetime.now().astimezone().isoformat(),**report}
        save('preview-built.json' if preview else 'built.json',data)
        return dict(status='ready',**data)
    finally:
        if temp.exists(): shutil.rmtree(temp)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','prepare','mark-published'])
    p.add_argument('--fingerprint');p.add_argument('--commit');p.add_argument('--deployment');p.add_argument('--url')
    a=p.parse_args()
    try:
        if a.action=='check':
            digest=fingerprint(ROOT);last=read('published.json')
            result={'status':'unchanged' if last.get('fingerprint')==digest else 'changed','fingerprint':digest,'last_published':last.get('published_at'),'url':last.get('url')}
        elif a.action=='prepare': result=prepare()
        else:
            built=read('built.json')
            if not all([a.fingerprint,a.commit,a.deployment,a.url]): raise ValueError('缺少已成功发布的版本信息')
            if built.get('fingerprint')!=a.fingerprint or built.get('output_hash')!=output_hash(): raise ValueError('构建已变化，不能把当前版本标记为已发布')
            result=dict(status='published',**built,commit=a.commit,deployment=a.deployment,url=a.url,published_at=datetime.now().astimezone().isoformat())
            save('published.json',result)
        print(json.dumps(result,ensure_ascii=False))
    except Exception as error:
        save('error.json',{'error':str(error),'at':datetime.now().astimezone().isoformat()})
        print(json.dumps({'status':'error','error':str(error)},ensure_ascii=False));sys.exit(1)
if __name__=='__main__':main()
