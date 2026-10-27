"""Edge-gated message-passing network over the electrode graph (P15.5).

Input per window: node features `(B, N, F_node)`, optional edge features `(B, N, N, F_edge)` and optional
graph-level features `(B, F_graph)` (FBCCA scores). Node encoder Linear + ELU plus a learned channel embedding
(N(0, 0.1)); `n_layers` x `EdgeGatedLayer`; readout concat(mean, max over nodes) -> dropout -> concat graph features
-> Linear. Edges are the complete graph without self loops (messages come from the other nodes only).
"""

from typing import Optional

import torch
from torch import nn

EMBED_STD = 0.1


class EdgeGatedLayer(nn.Module):
  """`LayerNorm(h + Dropout(ELU(W_self h_i + agg_i)))`, `agg_i` = mean over the other nodes j of `gate_ij * W_msg h_j`.

  `gate_ij = sigmoid(Linear(e_ij))` (one gate per hidden unit) when `n_edge_feats > 0`, else 1.
  `W_self` and `W_msg` carry no bias (R-8: the exact counts 5,150 / 5,534 need it; literal default-bias layers give
  5,278 / 5,662, i.e. +128 = 2 layers x 2 x 32; the gate Linear and the head keep their bias; B004 precedent).
  """

  def __init__(self, hidden: int, n_edge_feats: int = 0, dropout: float = 0.3):
    super().__init__()
    self.w_self = nn.Linear(hidden, hidden, bias=False)
    self.w_msg = nn.Linear(hidden, hidden, bias=False)
    self.gate = nn.Linear(n_edge_feats, hidden) if n_edge_feats > 0 else None
    self.act = nn.ELU()
    self.drop = nn.Dropout(dropout)
    self.norm = nn.LayerNorm(hidden)

  def forward(self, h: torch.Tensor, e: Optional[torch.Tensor] = None) -> torch.Tensor:
    n = h.shape[1]
    msg = self.w_msg(h)                                    # (B, N, H), message of node j
    off = 1.0 - torch.eye(n, dtype=h.dtype, device=h.device)   # no self messages
    if self.gate is not None:
      if e is None:
        raise ValueError("this layer has an edge gate; pass edge features")
      g = torch.sigmoid(self.gate(e))                      # (B, N, N, H), [b, i, j]
      agg = (g * msg.unsqueeze(1) * off[None, :, :, None]).sum(dim=2)
    else:
      agg = torch.einsum("ij,bjh->bih", off, msg)
    agg = agg / max(n - 1, 1)
    return self.norm(h + self.drop(self.act(self.w_self(h) + agg)))


class ConnectivityGNN(nn.Module):
  def __init__(self, n_nodes: int, n_node_feats: int, n_edge_feats: int = 0, n_graph_feats: int = 0,
               n_classes: int = 5, hidden: int = 32, n_layers: int = 2, dropout: float = 0.3):
    super().__init__()
    self.n_nodes, self.n_edge_feats, self.n_graph_feats = n_nodes, n_edge_feats, n_graph_feats
    self.encoder = nn.Sequential(nn.Linear(n_node_feats, hidden), nn.ELU())
    self.embed = nn.Parameter(torch.randn(n_nodes, hidden) * EMBED_STD)
    self.layers = nn.ModuleList([EdgeGatedLayer(hidden, n_edge_feats, dropout) for _ in range(n_layers)])
    self.drop = nn.Dropout(dropout)
    self.head = nn.Linear(2 * hidden + n_graph_feats, n_classes)

  def forward(self, x: torch.Tensor, e: Optional[torch.Tensor] = None, g: Optional[torch.Tensor] = None) -> torch.Tensor:
    h = self.encoder(x) + self.embed
    for layer in self.layers:
      h = layer(h, e)
    z = self.drop(torch.cat([h.mean(dim=1), h.max(dim=1).values], dim=1))
    if self.n_graph_feats > 0:
      if g is None:
        raise ValueError("model expects graph features")
      z = torch.cat([z, g], dim=1)
    return self.head(z)


def count_parameters(model: nn.Module) -> int:
  return sum(p.numel() for p in model.parameters() if p.requires_grad)
