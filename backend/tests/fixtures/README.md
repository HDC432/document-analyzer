# Test Fixtures

把腾讯年报命名为 `tencent_2025.pdf` 放入此目录。
测试会自动检测文件是否存在，不存在则跳过相关测试（pytest.skip）。

```
backend/tests/fixtures/
└── tencent_2025.pdf   ← 放这里（已加入 .gitignore，不会提交到 git）
```
