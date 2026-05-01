"""Machine learning module for the analytics layer.

Components:
- features   — Feature engineering from price bars (14 features)
- models     — ML model interface + MomentumMLStrategy
- sentiment  — News/social sentiment scoring (planned)
"""
from .features import extract_features, get_feature_names
from .models import MomentumMLStrategy
