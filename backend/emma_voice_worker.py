"""Continuous MOSS decode used by the approved Emma narration, without chunk seams."""
from pathlib import Path
import runpy
import sys
import numpy as np

# The bridge supplies the selected Emma source path through a process-local env.
import os
source = Path(os.environ['ZENIT_EMMA_VOICE_SOURCE']).resolve() / 'electron'
sys.path.insert(0, str(source))
import moss_streaming

class ContinuousVoice(moss_streaming.MossAudioStream):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack.close()
        self.buffered = True

    def pace(self, milliseconds):
        self.paces.append(milliseconds)

    def decode(self):
        if not self.frames:
            return
        import torch
        codes = torch.from_numpy(np.stack(self.frames).T[:, None, :].copy()).to(self.device)
        self.frames.clear()
        result = self.codec.decode(codes, return_dict=True)
        audio = result.audio[0, 0, :int(result.audio_lengths[0])].float().cpu().numpy()
        self.filter.audio = np.asarray(audio, dtype=np.float64)
        clean = self.filter.clean(self.filter.audio)
        peak = float(np.max(np.abs(clean)))
        if peak > .85:
            clean *= .85 / peak
        self.filter.emitted = len(audio)
        self.deliver(clean)

moss_streaming.MossAudioStream = ContinuousVoice
runpy.run_path(str(source / 'moss_voice_worker.py'), run_name='__main__')
