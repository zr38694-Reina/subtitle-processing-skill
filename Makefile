.PHONY: install install-dev clean test pip-uninstall

# === 安装 ===

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# 一键安装到 Claude Skills（可选）
install-skill:
	mkdir -p ~/.claude/skills
	ln -sfn "$(PWD)" ~/.claude/skills/subtitle-processing
	@echo "Skill linked to ~/.claude/skills/subtitle-processing"

# === 清理 ===

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

pip-uninstall:
	pip uninstall subtitle-processor -y

# === 测试 ===

test:
	python3 -m subtitle_processor --help
	@echo "---"
	@echo "Run a quick smoke test on a sample file..."
	python3 -c "
import tempfile, os
sample = '''1
00:00:00,000 --> 00:00:02,000
那各位同学大家好呀

2
00:00:02,000 --> 00:00:04,000
我们今天来学习这样一个啊

3
00:00:04,000 --> 00:00:06,000
大圆模型的基本概念
'''
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    f.write(sample)
    tmp = f.name
try:
    import subprocess
    r = subprocess.run(['python3', '-m', 'subtitle_processor', tmp, '--verbose'], capture_output=True, text=True)
    print(r.stdout)
finally:
    os.unlink(tmp)
"
	@echo "Smoke test passed!"

# === 打包 ===

build: clean
	pip install build
	python3 -m build
	@echo "Build complete: dist/"

# === 发布到 PyPI（需 twine）===

publish: build
	pip install twine
	twine upload dist/*
