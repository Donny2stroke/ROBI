import unittest
from robi.server import Core

class TestCore(unittest.TestCase):
    def test_initial(self):
        c=Core(); s=c.snapshot(); self.assertEqual(s['state'],'idle'); self.assertEqual(s['gaze_x'],0)
    def test_command(self):
        c=Core();s=c.command({'state':'happy','gaze_x':.5,'blink':True});self.assertEqual(s['state'],'happy');self.assertEqual(s['gaze_x'],.5);self.assertEqual(s['blink_id'],1)
    def test_reject_out_of_range(self):
        with self.assertRaises(ValueError): Core().command({'gaze_y':4})
    def test_reject_unknown_state(self):
        with self.assertRaises(ValueError): Core().command({'state':'unknown'})
    def test_reject_nan(self):
        with self.assertRaises(ValueError): Core().command({'gaze_x':float('nan')})

if __name__=='__main__':unittest.main()
