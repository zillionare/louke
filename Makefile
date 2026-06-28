# holdpoint Makefile
# 单一来源管理: agents/ 和 templates/ 在包外，holdpoint/agents/ 和 holdpoint/templates/ 是 wheel 数据副本

.PHONY: sync-data build install test clean uninstall

# 把 agents/ 和 templates/ 同步到 holdpoint/ 包数据目录（构建 wheel 前必跑）
sync-data:
	@echo "== syncing agents/ -> holdpoint/agents/"
	@rm -rf holdpoint/agents
	@cp -r agents holdpoint/agents
	@echo "== syncing templates/ -> holdpoint/templates/"
	@rm -rf holdpoint/templates
	@cp -r templates holdpoint/templates
	@echo "✓ synced: $$(ls holdpoint/agents | wc -l) agents, $$(ls holdpoint/templates | wc -l) templates"

# 构建 wheel + sdist
build: sync-data
	@rm -rf dist build
	@python3 -m build
	@echo "✓ built: $$(ls dist/)"

# 在当前 venv 安装 holdpoint
install: build
	@pip install --force-reinstall --no-deps dist/holdpoint-*.whl
	@echo "✓ installed: hp → $$(which hp)"

# 跑测试 (bats)
test:
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/*.bats; \
	else \
		echo "bats not installed. Install: brew install bats-core"; \
		exit 1; \
	fi

# 从当前 venv 卸载
uninstall:
	@pip uninstall -y holdpoint

# 清理构建产物
clean:
	@rm -rf dist build holdpoint.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ cleaned"
