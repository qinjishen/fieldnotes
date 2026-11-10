"""One editable vault must produce stable URLs and portable published snapshots."""
from pathlib import Path
import json, shutil, tempfile, unittest, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from setup_obsidian import setup
from publishing import Library, fingerprint, parse

class ObsidianTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for name in ['content','templates']:shutil.copytree(ROOT/name,self.root/name)
        self.vault=self.root/'发布文档';self.vault.mkdir()
        (self.vault/'随记.md').write_text('---\nid: journal\n---\n# 随记\n\n真实记录。')
        self.out=self.root/'out';self.out.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def test_migration_edit_rename_and_snapshot_assets(self):
        before=Library(self.root,self.out)
        report=setup(self.root);self.assertEqual(report['articles'],10)
        lib=Library(self.root,self.out)
        self.assertEqual(set(before.by_id),set(lib.by_id))
        for cid in before.by_id:
            self.assertEqual(before.by_id[cid]['body'],lib.by_id[cid]['body'])
            self.assertEqual(before.by_id[cid]['related'],lib.by_id[cid]['related'])
        p=lib.by_id['o001']['_path'];self.assertTrue(p.is_relative_to(self.vault))
        changed=p.read_text()+'\n\n新增可核实记录。[[journal]]\n\n![[附件/示意.png]]\n'
        (self.vault/'附件/示意.png').write_bytes(b'png-test')
        p.write_text(changed);p.rename(p.with_name('重新命名.md'))
        digest=fingerprint(self.root)
        edited=Library(self.root,self.out);self.assertIn('新增可核实',edited.by_id['o001']['body'])
        self.assertIn('journal.html',edited.by_id['o001']['_html'])
        edited.snapshot();self.assertEqual(digest,fingerprint(self.root),'snapshot must not change source fingerprint')
        raw=parse(self.root/'content/cards/o001.md')[1];self.assertIn('新增可核实',raw)
        payload=json.loads((self.root/'content/published.json').read_text());self.assertEqual(len(payload),10)
        shutil.rmtree(self.vault)
        replay=Library(self.root,self.root/'replay')
        self.assertEqual(len(replay.cards),10)
        self.assertEqual(replay.by_id['o001']['_html'],edited.by_id['o001']['_html'])
        self.assertTrue(list((self.root/'replay/assets').glob('*.png')))
        self.assertEqual(replay.by_id['o001']['sources'],edited.by_id['o001']['sources'])
    def test_repeat_setup_keeps_edits_and_private_templates(self):
        setup(self.root);lib=Library(self.root,self.out);p=lib.by_id['o002']['_path'];p.write_text(p.read_text()+'\n\n用户新写的正文。\n')
        setup(self.root);lib=Library(self.root,self.out)
        self.assertIn('用户新写',lib.by_id['o002']['body'])
        self.assertEqual(len(lib.cards),10)
        ids=[c['id'] for c in lib.cards];self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue((self.vault/'_开始写作.md').exists())
        settings=json.loads((self.vault/'.obsidian/templates.json').read_text());self.assertEqual(settings['folder'],'_写作模板')
        self.assertEqual(len(list((self.vault/'_写作模板').glob('*.md'))),4)
    def test_graph_projection_keeps_note_aliases_unchanged(self):
        from portal import graph_data
        setup(self.root);lib=Library(self.root,self.out)
        before=list(lib.by_id['o001']['aliases'])
        graph=graph_data(lib.cards,lib.cards)
        next(n for n in graph['nodes'] if n['id']=='o001')['aliases'].append('搜索辅助词')
        self.assertEqual(lib.by_id['o001']['aliases'],before)

    def test_hidden_handoff_config_changes_fingerprint(self):
        before=fingerprint(self.root);setup(self.root);after=fingerprint(self.root)
        self.assertNotEqual(before,after)
        config=self.vault/'.obsidian/fieldnotes.json';d=json.loads(config.read_text());d['schema']=2;config.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'配置无效'):Library(self.root,self.out)

if __name__=='__main__':unittest.main()
