"""Growth metadata must survive publication without inventing personal events."""
import json, shutil, tempfile, unittest
from pathlib import Path
from publishing import Library, fingerprint
from portal import render_growth_home

ROOT = Path(__file__).resolve().parents[1]

class GrowthTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'content',self.root/'content')
        self.inputs=self.root/'发布文档';self.inputs.mkdir()
        self.out=self.root/'out';self.out.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,text):
        p=self.inputs/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def test_metadata_and_template_survive_snapshot(self):
        self.write('进展.md','---\nid: real-progress\nstage: progress\nshort_title: 阶段检查\nevent_date: 2026-10-12\n---\n# 一次有日期的记录\n\n事实和 [[o006]]。')
        self.write('模版/练习.md','# 练习表格\n\n这是模板。')
        lib=Library(self.root,self.out)
        progress=lib.by_id['real-progress']
        self.assertEqual(progress['event_date'],'2026-10-12')
        self.assertEqual(progress['short_title'],'阶段检查')
        template=next(c for c in lib.cards if c['title']=='练习表格')
        self.assertTrue(template['is_template']);self.assertEqual(template['kind'],'模板')
        self.assertEqual(template['event_date'],'')
        lib.snapshot();shutil.rmtree(self.inputs)
        replay=Library(self.root,self.root/'replay')
        self.assertEqual(replay.by_id['real-progress']['stage'],'progress')
        self.assertEqual(replay.by_id['real-progress']['event_date'],'2026-10-12')
        self.assertTrue(replay.by_id[template['id']]['is_template'])
        self.assertIn('事实和',replay.by_id['real-progress']['body'])
        self.assertEqual(replay.by_id['real-progress']['related'][0]['id'],'o006')
    def test_reusable_templates_trigger_sync_without_becoming_articles(self):
        before=fingerprint(self.root)
        (self.root/'templates').mkdir()
        (self.root/'templates/新模板.md').write_text('# 模板说明')
        self.assertNotEqual(before,fingerprint(self.root))
        self.assertEqual(len(Library(self.root,self.out).cards),9)

    def test_invalid_metadata_blocks_build(self):
        p=self.write('记录.md','---\nstage: made-up\n---\n# 记录\n\n正文')
        with self.assertRaisesRegex(ValueError,'stage'):Library(self.root,self.out)
        p.write_text('---\nevent_date: "2026-02-30"\n---\n# 记录\n\n正文')
        with self.assertRaisesRegex(ValueError,'event_date'):Library(self.root,self.out)
    def test_home_uses_real_notes_and_explicit_edges(self):
        self.write('模板.md','---\nkind: template\n---\n# 模板标题\n\n[[o001]]')
        lib=Library(self.root,self.out)
        render_growth_home(self.out,lib.cards,{},lambda title,body,**kwargs:body)
        data=json.loads((self.out/'growth-graph.json').read_text())
        self.assertEqual(len(data['nodes']),9)
        self.assertEqual(sum(n['stage']=='application' for n in data['nodes']),3)
        self.assertFalse(any(n['event_date'] for n in data['nodes']))
        ids={n['id'] for n in data['nodes']}
        expected={tuple(sorted((c['id'],r['id']))) for c in lib.cards for r in c['related'] if c['id'] in ids and r['id'] in ids}
        self.assertEqual({(e['a'],e['b']) for e in data['edges']},expected)
        home=(self.out/'index.html').read_text()
        self.assertNotIn('模板标题',home)
        self.assertIn('新的进展',home)
        for cid in ids:self.assertIn(f'cards/{cid}.html',home)

if __name__=='__main__':unittest.main()
