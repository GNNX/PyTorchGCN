import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch_geometric.transforms as T
from torch_geometric.nn import GCNConv, global_mean_pool


class GCN(torch.nn.Module):

    def __init__(self):
        super().__init__()

        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim
        self.n_classes = n_classes

        self.embedding_h = nn.Linear(self.in_dim, self.hidden_dim)

        self.conv1 = GCNConv(self.hidden_dim, self.hidden_dim, cached=True, normalize=True)
        self.conv2 = GCNConv(self.hidden_dim, self.hidden_dim, cached=True, normalize=True)
        self.conv3 = GCNConv(self.hidden_dim, self.hidden_dim, cached=True, normalize=True)
        self.conv4 = GCNConv(self.hidden_dim, self.out_dim, cached=True, normalize=True)

        self.read_out1 = nn.Linear(self.out_dim, self.out_dim // 2, bias=True)
        self.read_out2 = nn.Linear(self.out_dim // 2, self.out_dim // 4, bias=True)
        self.read_out3 = nn.Linear(self.out_dim // 4, self.n_classes, bias=True)

        self.relu = nn.ReLU()
        pass

    def forward(self, x, edge_index, edge_weight):
        embedding_x = self.embedding_h(x)

        gcn_conv1 = self.relu(self.conv1(embedding_x, edge_index, edge_weight))
        gcn_conv2 = self.relu(self.conv2(gcn_conv1, edge_index, edge_weight))
        gcn_conv3 = self.relu(self.conv3(gcn_conv2, edge_index, edge_weight))
        gcn_conv4 = self.relu(self.conv4(gcn_conv3, edge_index, edge_weight))

        batch = None
        aggr_out = global_mean_pool(gcn_conv4, batch)

        read_out1 = self.relu(self.read_out1(aggr_out))
        read_out2 = self.relu(self.read_out2(read_out1))
        read_out3 = self.read_out3(read_out2)
        return read_out3

    pass


