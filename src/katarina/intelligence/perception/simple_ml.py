from __future__ import annotations
from dataclasses import dataclass
from math import exp
from typing import Sequence

@dataclass(frozen=True, slots=True)
class LogisticModel:
    weights: tuple[float,...]
    bias: float
    version: str
    def predict_proba(self, x: Sequence[float]) -> float:
        if len(x)!=len(self.weights): raise ValueError("feature_count")
        z=self.bias+sum(w*v for w,v in zip(self.weights,x))
        z=max(-60.0,min(60.0,z))
        return 1.0/(1.0+exp(-z))

class MachineLearningV1:
    def train(self, xs: Sequence[Sequence[float]], ys: Sequence[int], *, epochs: int=100, lr: float=0.1, version: str="candidate") -> LogisticModel:
        if not xs or len(xs)!=len(ys): raise ValueError("dataset")
        n=len(xs[0])
        if n==0 or any(len(x)!=n for x in xs) or any(y not in (0,1) for y in ys): raise ValueError("dataset")
        w=[0.0]*n; b=0.0
        for _ in range(epochs):
            gw=[0.0]*n; gb=0.0
            for x,y in zip(xs,ys):
                z=max(-60.0,min(60.0,b+sum(a*c for a,c in zip(w,x))))
                p=1.0/(1.0+exp(-z)); e=p-y
                for i,v in enumerate(x): gw[i]+=e*v
                gb+=e
            scale=1.0/len(xs)
            w=[a-lr*g*scale for a,g in zip(w,gw)]; b-=lr*gb*scale
        return LogisticModel(tuple(w),b,version)
