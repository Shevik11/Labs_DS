import random


def interval(values, n=2000):
    # Standard-library bootstrap so report generation needs no ML dependencies.
    rng=random.Random(42)
    samples=sorted(sum(rng.choices(values,k=len(values)))/len(values) for _ in range(n))
    return [samples[int(.025*(n-1))],samples[int(.975*(n-1))]]
