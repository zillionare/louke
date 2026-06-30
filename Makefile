# louke Makefile
# 单一来源管理: agents/ 和 templates/ 在包外，louke/agents/ 和 louke/templates/ 是 wheel 数据副本

.PHONY: sync-data build install test clean uninstall

# 把 agents/ 和 templates/ 同步到 louke/ 包数据目录（构建 wheel 前必跑）
sync-data:
	@echo "== syncing agents/ -> louke/agents/"
	@rm -rf louke/agents
	@cp -r agents louke/agents
	@echo "== syncing templates/ -> louke/templates/"
	@rm -rf louke/templates
	@cp -r templates louke/templates
	@echo "== syncing .github resources -> louke/.github/"
	@rm -rf louke/.github
	@mkdir -p louke/.github
	@cp -r .github/ISSUE_TEMPLATE louke/.github/ISSUE_TEMPLATE
	@if [ -d .github/workflows ]; then cp -r .github/workflows louke/.github/workflows; fi
	@echo "✓ synced: $$(ls louke/agents | wc -l) agents, $$(ls louke/templates | wc -l) templates"

# 构建 wheel + sdist
build: sync-data
	@rm -rf dist build
	@python3 -m build
	@echo "✓ built: $$(ls dist/)"

# 在当前 venv 安装 louke
install: build
	@pip install --force-reinstall --no-deps dist/louke-*.whl
	@echo "✓ installed: lk → $$(which lk)"

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
	@pip uninstall -y louke

# 清理构建产物
clean:
	@rm -rf dist build louke.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ cleaned"
