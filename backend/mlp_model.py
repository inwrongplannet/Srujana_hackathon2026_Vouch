"""PyTorch MLP model for default prediction on combined3 data."""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, accuracy_score, f1_score
import torch
from torch.utils.data import DataLoader, Dataset

d = r'C:\Users\Noodl\AppData\Local\Temp\opencode\combined3\combined'

class MLPDataset(Dataset):
    def __init__(self, features_df, labels):
        self.features = features_df.values.astype(np.float32)
        self.labels = labels.astype(np.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


class MLP(torch.nn.Module):
    def __init__(self, n_feats):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(n_feats, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
            torch.nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


features = [
    'pre_bureau_score', 'post_bureau_score', 'bureau_drop_points',
    'pre_vouch_score', 'post_vouch_score', 'vouch_held',
    'shock_type', 'severity', 'insured',
    'support_mobilised_minor', 'support_before_application_minor',
]

se = pd.read_csv(os.path.join(d, 'shock_events.csv'))
vs = pd.read_csv(os.path.join(d, 'vouch_scores.csv'))
vo = pd.read_csv(os.path.join(d, 'vouch_outcomes.csv'))
m = se.merge(vs, on='borrower_id', how='left').merge(vo, on='borrower_id', how='left')

y = m['y'].to_numpy()
X = m[features].copy()

# Drop rows with NaN in target or features
valid = ~pd.isna(y)
for c in features:
    if X[c].isna().any():
        valid = valid & ~X[c].isna()

X = X[valid]
y = y[valid]

# Encode categorical columns
X_enc = X.copy()
X_enc['shock_type'] = X_enc['shock_type'].astype('category').cat.codes
X_enc['severity'] = X_enc['severity'].astype('category').cat.codes
X_enc['insured'] = X_enc['insured'].astype(int)

n_feats = X_enc.shape[1]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_enc, y, test_size=0.2, random_state=42, stratify=y)

train_dataset = MLPDataset(X_enc.loc[X_train.index], y_train)
test_dataset = MLPDataset(X_enc.loc[X_test.index], y_test)

train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

model = MLP(n_feats).to(device)

criterion = torch.nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Train 10 epochs
for epoch in range(10):
    model.train()
    epoch_loss = 0.0
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        preds = model(xb).squeeze()
        loss = criterion(preds, yb)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    print(f'Epoch {epoch+1}/10, loss: {epoch_loss/len(train_loader):.4f}')

# Evaluate
model.eval()
all_preds = []
all_true = []
with torch.no_grad():
    for xb, yb in test_loader:
        xb = xb.to(device)
        preds = model(xb).squeeze().cpu().numpy()
        all_preds.append(preds)
        all_true.append(yb.cpu().numpy())

p = np.concatenate(all_preds)
t = np.concatenate(all_true)

th = 0.5
metrics = {
    'auc': round(float(roc_auc_score(t, p)), 4),
    'pr_auc': round(float(average_precision_score(t, p)), 4),
    'brier': round(float(brier_score_loss(t, p)), 4),
    'accuracy': round(float(accuracy_score(t, (p >= th).astype(int))), 4),
    'f1': round(float(f1_score(t, (p >= th).astype(int), zero_division=0)), 4),
}

print('\n=== Model 1: Loan eligibility (PyTorch MLP) ===')
for k, v in metrics.items():
    print(f'  {k}: {v}')

# Feature importance via first layer weights
with torch.no_grad():
    w = model.net[0].weight.detach().cpu().numpy()[0]
    feat_imp = sorted(zip(features, np.abs(w)), key=lambda x: x[1], reverse=True)
    print('\nTop features (by weight magnitude):')
    for f, v in feat_imp:
        print(f'  {f}: {v:.4f}')

# Save metrics
import json
os.makedirs('results', exist_ok=True)
with open('results/mlp_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
print('\nMetrics saved to results/mlp_metrics.json')

# === Model 2: CIBIL fall + vouch explanation ===
print('\n=== Model 2: CIBIL fall + vouch held ===')
drop_mask = m['bureau_drop_points'] > 0
vh_mask = m['vouch_held'] == 1
sub = m[drop_mask & vh_mask].copy()
print(f'Borrowers with bureau drop AND vouch held: {len(sub)}')
if len(sub) > 0:
    print(f'Mean bureau drop: {sub.bureau_drop_points.mean():.1f}')
    print(f'Mean pre vouch score: {sub.pre_vouch_score.mean():.1f}')
    print(f'Mean post vouch score: {sub.post_vouch_score.mean():.1f}')
    print(f'Mean post bureau score: {sub.post_bureau_score.mean():.1f}')
    print(f'Default rate: {sub.y.mean():.4f}')

    # Compare to bureau drop without vouch held
    sub0 = m[drop_mask & (~vh_mask)]
    print(f'\nBureau drop, no vouch held: {len(sub0)} borrowers')
    print(f'Default rate: {sub0.y.mean():.4f}')
    print(f'Mean bureau drop: {sub0.bureau_drop_points.mean():.1f}')
    print(f'Mean pre vouch score: {sub0.pre_vouch_score.mean():.1f}')
    print(f'Mean post vouch score: {sub0.post_vouch_score.mean():.1f}')
    print(f'\nKey: vouch held associated with {sub.y.mean()-sub0.y.mean():.4f} higher default rate')
else:
    print('No borrowers with bureau drop + vouch held in this sample')

# Save combined results
results = {**metrics, 'cibil_fall_vouch': {
    'n_borrowers': int(len(sub)) if len(sub) > 0 else 0,
    'mean_bureau_drop': float(sub.bureau_drop_points.mean()) if len(sub) > 0 else None,
    'mean_pre_vouch': float(sub.pre_vouch_score.mean()) if len(sub) > 0 else None,
    'mean_post_vouch': float(sub.post_vouch_score.mean()) if len(sub) > 0 else None,
    'default_rate': float(sub.y.mean()) if len(sub) > 0 else None,
    'delta_vs_no_vouch': float(sub.y.mean() - sub0.y.mean()) if len(sub) > 0 and len(sub0) > 0 else None,
}}
with open('results/combined_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('\nCombined results saved to results/combined_results.json')