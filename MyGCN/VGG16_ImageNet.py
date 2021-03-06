import os
import torch
import numpy as np
import torchvision
import torch.nn as nn
import torch.optim as optim
from alisuretool.Tools import Tools
import torchvision.transforms as transforms


class ConvBlock(nn.Module):

    def __init__(self, cin, cout, stride=1, padding=1, ks=3, has_relu=True, has_bn=True, bias=True):
        super().__init__()
        self.has_relu = has_relu
        self.has_bn = has_bn

        self.conv = nn.Conv2d(cin, cout, kernel_size=ks, stride=stride, padding=padding, bias=bias)
        self.bn = nn.BatchNorm2d(cout)
        self.relu = nn.ReLU(inplace=True)
        pass

    def forward(self, x):
        out = self.conv(x)
        if self.has_bn:
            out = self.bn(out)
        if self.has_relu:
            out = self.relu(out)
        return out

    pass


class GCNBlock(nn.Module):

    def __init__(self, cin=146, cout=146, padding=0, ks=1, has_relu=True, has_bn=True):
        super().__init__()
        self.has_bn = has_bn
        self.has_relu = has_relu
        self.pool = nn.AvgPool2d(3, 1, padding=1)
        self.conv = ConvBlock(cin, cout, padding=padding, ks=ks, has_bn=self.has_bn, has_relu=self.has_relu)
        pass

    def forward(self, e):
        e = self.conv(e)
        e = self.pool(e)
        return e

    pass


class VGG2(nn.Module):

    def __init__(self):
        super(VGG2, self).__init__()
        self.features = self._make_layers()
        self.classifier = nn.Linear(1024, 1000)
        pass

    def forward(self, x):
        out = self.features(x)
        out = out.view(out.size(0), -1)
        out = self.classifier(out)
        return out

    @staticmethod
    def _make_layers():
        layers = [
            ConvBlock(3, 64, ks=3, padding=1),  # 224
            nn.MaxPool2d(kernel_size=2, stride=2),  # 112
            ConvBlock(64, 128, ks=3, padding=1),
            ConvBlock(128, 128, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 56

            GCNBlock(128, 256, ks=1, padding=0),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 28
            GCNBlock(256, 256, ks=1, padding=0),
            nn.AvgPool2d(kernel_size=2, stride=2),  # 14

            GCNBlock(256, 512, ks=1, padding=0),
            GCNBlock(512, 512, ks=1, padding=0),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 7
            GCNBlock(512, 1024, ks=1, padding=0),
            GCNBlock(1024, 1024, ks=1, padding=0),
            nn.AdaptiveAvgPool2d(1)
        ]
        return nn.Sequential(*layers)

    @staticmethod
    def _make_layers1():
        layers = [
            ConvBlock(3, 64, ks=3, padding=1),
            ConvBlock(64, 64, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),
            ConvBlock(64, 128, ks=3, padding=1),
            ConvBlock(128, 128, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),
            ConvBlock(128, 256, ks=3, padding=1),
            ConvBlock(256, 256, ks=3, padding=1),
            ConvBlock(256, 256, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),
            ConvBlock(256, 512, ks=3, padding=1),
            ConvBlock(512, 512, ks=3, padding=1),
            ConvBlock(512, 512, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),
            ConvBlock(512, 512, ks=3, padding=1),
            ConvBlock(512, 512, ks=3, padding=1),
            ConvBlock(512, 512, ks=3, padding=1),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.AdaptiveAvgPool2d(1)
        ]
        return nn.Sequential(*layers)

    pass


class Runner(object):

    def __init__(self, root_path='/mnt/4T/Data/cifar/cifar-10', batch_size=128, lr=0.1):
        self.root_path = root_path
        self.batch_size = batch_size
        self.lr = lr

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.best_acc = 0
        self.start_epoch = 0

        self.net = VGG2().to(self.device)
        self.criterion = nn.CrossEntropyLoss()

        self.optimizer = optim.SGD(self.net.parameters(), lr=self.lr, momentum=0.9, weight_decay=5e-4)
        # self.optimizer = optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=0.0)

        self.train_loader, self.test_loader = self._data()
        pass

    def _data(self):
        Tools.print('==> Preparing data..')
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

        transform_train = transforms.Compose([transforms.RandomResizedCrop(224),
                                              transforms.RandomHorizontalFlip(),
                                              transforms.ToTensor(), normalize])
        transform_test = transforms.Compose([transforms.Resize(256), transforms.CenterCrop(224),
                                             transforms.ToTensor(), normalize])

        _train_dir = os.path.join(self.root_path, "train")
        _test_dir = os.path.join(self.root_path, "val_new")

        train_set = torchvision.datasets.ImageFolder(_train_dir, transform=transform_train)
        _train_loader = torch.utils.data.DataLoader(train_set, batch_size=self.batch_size, shuffle=True, num_workers=8)

        test_set = torchvision.datasets.ImageFolder(_test_dir, transform=transform_test)
        _test_loader = torch.utils.data.DataLoader(test_set, batch_size=100, shuffle=False, num_workers=8)

        return _train_loader, _test_loader

    def _change_lr(self, epoch):

        def __change_lr(_lr):
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = _lr
            pass

        if 0 <= epoch < 33:
            __change_lr(self.lr)
        elif 33 <= epoch < 66:
            __change_lr(self.lr / 10)
        elif 66 <= epoch:
            __change_lr(self.lr / 100)

        pass

    @staticmethod
    def _view_model_param(model):
        total_param = 0
        for param in model.parameters():
            total_param += np.prod(list(param.data.size()))
        return total_param

    def info(self):
        Tools.print("batch size={} lr={}".format(self.batch_size, self.lr))
        Tools.print("{} ".format(self._view_model_param(self.net)))
        pass

    def train(self, epoch, change_lr=False):
        print()
        Tools.print('Epoch: %d' % epoch)

        if change_lr:
            self._change_lr(epoch)

        self.net.train()
        train_loss = 0
        correct = 0
        total = 0
        for batch_idx, (inputs, targets) in enumerate(self.train_loader):
            inputs, targets = inputs.to(self.device), targets.to(self.device)
            self.optimizer.zero_grad()
            outputs = self.net(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            if batch_idx % 1000 == 0:
                Tools.print('Loss: %.3f | Acc: %.3f%% (%d/%d, %d/%d)'
                           % (train_loss / (batch_idx + 1), 100. * correct / total,
                              correct, total, batch_idx, len(self.train_loader)))
            pass
        Tools.print('Loss: %.3f | Acc: %.3f%% (%d/%d)'
                   % (train_loss / len(self.train_loader), 100. * correct / total, correct, total))
        pass

    def test(self, epoch):
        self.net.eval()
        test_loss = 0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_idx, (inputs, targets) in enumerate(self.test_loader):
                inputs, targets = inputs.to(self.device), targets.to(self.device)
                outputs = self.net(inputs)
                loss = self.criterion(outputs, targets)

                test_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                pass
            pass

        Tools.print('Loss: %.3f | Acc: %.3f%% (%d/%d)'
                   % (test_loss / len(self.test_loader), 100. * correct / total, correct, total))
        Tools.print("best_acc={} acc={}".format(self.best_acc, 100. * correct / total))
        pass

    pass


if __name__ == '__main__':
    """
    34 46.61
    """

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 1

    _data_root_path = "/media/ubuntu/ALISURE-SSD/data/ImageNet/ILSVRC2015/Data/CLS-LOC"
    # _data_root_path = '/mnt/4T/Data/ILSVRC17/ILSVRC2015_CLS-LOC/ILSVRC2015/Data/CLS-LOC'

    runner = Runner(root_path=_data_root_path, batch_size=64, lr=0.01)
    runner.info()

    for _epoch in range(runner.start_epoch, 100):
        runner.train(_epoch, change_lr=True)
        runner.test(_epoch)
        pass

    pass
