"""Observable facial action signals, NOT emotions or personal traits.

Blendshape scores are model outputs (not calibrated probabilities of feelings).
"""
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ExpressionSignals:
    smile: float = 0.0
    brow_lowering: float = 0.0
    brow_raising: float = 0.0
    mouth_open: float = 0.0
    eye_widening: float = 0.0

    def to_dict(self):
        return asdict(self)


def from_blendshapes(categories):
    """Turn MediaPipe's named coefficient list into a few interpretable signals."""
    scores = {item.category_name: float(item.score) for item in categories}
    def avg(*names):
        return sum(scores.get(n, 0.0) for n in names) / len(names)
    return ExpressionSignals(
        smile=avg('mouthSmileLeft', 'mouthSmileRight'),
        brow_lowering=avg('browDownLeft', 'browDownRight'),
        brow_raising=scores.get('browInnerUp', 0.0),
        mouth_open=scores.get('jawOpen', 0.0),
        eye_widening=avg('eyeWideLeft', 'eyeWideRight'),
    )
