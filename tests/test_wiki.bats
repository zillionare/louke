#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "WIKI-001: Librarian mentions .louke/wiki/pages/ directory" {
    run grep -qE "\.louke/wiki/pages/" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention .louke/wiki/pages/"
        false
    }
}

@test "WIKI-002: Librarian mentions SHA256 incremental cache" {
    run grep -qE "SHA256" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention SHA256 incremental cache"
        false
    }
}

@test "WIKI-003: Librarian mentions index.md maintenance" {
    run grep -qE "index\.md" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention index.md"
        false
    }
}

@test "WIKI-004: Librarian mentions Lint/health check" {
    run grep -qE "(Lint|健康检查|孤立页面|死链接)" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention Lint or health check"
        false
    }
}

@test "WIKI-005: Librarian mentions wiki/pages/ frontmatter format" {
    run grep -qE "(frontmatter|YAML)" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention frontmatter or YAML"
        false
    }
}

@test "WIKI-006: No agent writes to obsolete wiki/entries/ path" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        # Skip Librarian (owns wiki structure). No other reference docs in agents/.
        case "$filename" in
            Librarian.md) continue ;;
        esac
        if grep -q "wiki/entries/" "$file"; then
            echo "FAIL: $filename still references wiki/entries/ instead of .louke/wiki/pages/"
            return 1
        fi
    done
}

@test "WIKI-007: All agents with session save write to .louke/raw/" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        case "$filename" in
            Librarian.md) continue ;;
        esac
        if grep -q "会话保存" "$file"; then
            grep -q "\.louke/raw/" "$file" || {
                echo "FAIL: $filename has session save but does not reference .louke/raw/"
                return 1
            }
        fi
    done
}

@test "WIKI-008: All agents with session save use new frontmatter format (status: field)" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        case "$filename" in
            Librarian.md) continue ;;
        esac
        if grep -q "会话保存" "$file"; then
            grep -q "status:" "$file" || {
                echo "FAIL: $filename session save does not include 'status:' frontmatter field"
                return 1
            }
        fi
    done
}
