import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from publishing import Library

class PublishingTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'content',self.root/'content')
        self.input=self.root/'发布文档';self.input.mkdir()
        self.out=self.root/'out';self.out.mkdir()
    def tearDown(self): self.tmp.cleanup()
    def write(self,name,body):
        p=self.input/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(body);return p
    def test_markdown_links_and_assets(self):
        self.write('甲.md','# 甲\n\n链接 [[乙#方法|接着读]] 和 [原文章](../missing.md)。\n\n![[附件/图片.png|300]]\n\n|项目|值|\n|---|---|\n|次数|3|\n\n```md\n[[代码中的链接]]\n```\n\n<script>alert(1)</script>')
        self.write('乙.md','---\nid: note-b\naliases: [第二篇]\n---\n# 乙\n\n## 方法\n\n正文。')
        (self.input/'附件').mkdir();(self.input/'附件/图片.png').write_bytes(b'png-test')
        lib=Library(self.root,self.out);a=next(c for c in lib.cards if c['title']=='甲')
        self.assertIn('note-b.html#%E6%96%B9%E6%B3%95',a['_html']);self.assertIn('<table>',a['_html'])
        self.assertIn('<img',a['_html']);self.assertIn('[[代码中的链接]]',a['_html'])
        self.assertNotIn('<script>',a['_html']);self.assertIn('note-b',[r['id'] for r in a['related']])
        self.assertEqual(len(lib.warnings),1)
        lib.snapshot();shutil.rmtree(self.input)
        replay=Library(self.root,self.root/'replay')
        self.assertEqual(len(replay.cards),11);self.assertIn('<table>',next(c for c in replay.cards if c['title']=='甲')['_html'])
    def test_plain_draft_and_domain(self):
        self.write('体能训练/简单.md','# 训练原则\n\n一段完整说明。')
        self.write('草稿.md','---\ndraft: true\n---\n# 私人草稿\n\n不应出现在网页、下载或快照中。')
        self.write('_备忘.md','# 不发布')
        lib=Library(self.root,self.out);lib.snapshot()
        self.assertEqual(len(lib.cards),10);self.assertEqual(lib.cards[-1]['domain'],'fitness')
        self.assertNotIn('私人草稿',(self.root/'content/published.json').read_text())
    def test_edit_and_delete(self):
        p=self.write('文章.md','# 标题\n\n旧内容')
        first=Library(self.root,self.out).cards[-1]['id']
        p.write_text('# 改标题\n\n新内容')
        lib=Library(self.root,self.out);self.assertEqual(lib.cards[-1]['id'],first)
        self.assertIn('新内容',lib.cards[-1]['_html']);p.unlink()
        self.assertEqual(len(Library(self.root,self.out).cards),9)
    def test_ambiguous_and_invalid(self):
        self.write('一/同名.md','# 同名\n\n一')
        self.write('二/同名.md','# 同名\n\n二')
        p=self.write('索引.md','# 索引\n\n[[同名]]')
        with self.assertRaisesRegex(ValueError,'多个同名'): Library(self.root,self.out)
        p.write_text('---\nid: o001\n---\n# 重复')
        with self.assertRaisesRegex(ValueError,'重复'): Library(self.root,self.out)
    def test_missing_image(self):
        self.write('文章.md','# 图\n\n![图](missing.png)')
        with self.assertRaisesRegex(ValueError,'附件'): Library(self.root,self.out)

if __name__=='__main__':unittest.main()

class BuildTest(unittest.TestCase):
    def test_atomic_build_removal_and_preview_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in ['build.py','redesign.py','publishing.py','portal.py']: shutil.copyfile(ROOT/f,root/f)
            for f in ['content','static','scripts']: shutil.copytree(ROOT/f,root/f)
            inputs=root/'发布文档';inputs.mkdir()
            note=inputs/'新增.md';note.write_text('---\nid: new-note\n---\n# 新增\n\n测试正文')
            def run(*args): return subprocess.run([sys.executable,str(root/'scripts/sync.py'),*args],capture_output=True,text=True,cwd=root)
            first=run('prepare');self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertTrue((root/'dist/cards/new-note.html').exists())
            before=(root/'dist/search-index.json').read_bytes()
            note.write_text('# 出错\n\n![找不到](missing.png)')
            failed=run('prepare');self.assertNotEqual(failed.returncode,0)
            self.assertEqual(before,(root/'dist/search-index.json').read_bytes())
            note.unlink();removed=run('prepare');self.assertEqual(removed.returncode,0,removed.stdout)
            self.assertFalse((root/'dist/cards/new-note.html').exists())
            self.assertFalse((root/'dist/markdown/new-note.md').exists())
            note.write_text('# 预览独有\n\n测试')
            before=(root/'dist/search-index.json').read_bytes()
            code="import sys;sys.path.insert(0,'scripts');from sync import prepare;prepare(preview=True)"
            preview=subprocess.run([sys.executable,'-c',code],cwd=root,capture_output=True,text=True)
            self.assertEqual(preview.returncode,0,preview.stderr)
            self.assertEqual(before,(root/'dist/search-index.json').read_bytes())
            self.assertNotIn('预览独有',(root/'content/published.json').read_text())

class PortalTest(unittest.TestCase):
    def test_plans_draft_folder_and_explicit_edges(self):
        from portal import graph_data
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(ROOT/'content',root/'content')
            plans=root/'发布文档/训练计划';plans.mkdir(parents=True)
            (plans/'本周.md').write_text('---\nid: weekly-plan\n---\n# 本周安排\n\n[[o001|参考观点]]')
            drafts=root/'发布文档/网球教学/草稿';drafts.mkdir(parents=True)
            (drafts/'重复.md').write_text('---\nid: o001\n---\n# 不应进入发布')
            lib=Library(root,root/'out');plan=next(c for c in lib.cards if c['id']=='weekly-plan')
            self.assertEqual(plan['domain'],'plans');self.assertEqual(len(lib.cards),10)
            graph=graph_data(lib.cards,lib.cards)
            expected={tuple(sorted((c['id'],r['id']))) for c in lib.cards for r in c['related']}
            self.assertEqual({(e['a'],e['b']) for e in graph['edges']},expected)
            self.assertEqual(len(graph['nodes']),10)
