#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "WIKI-001: Librarian mentions wiki/pages/ directory" {
    run grep -qE "wiki/pages/" "$AGENTS_DIR/Librarian.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Librarian.md does not mention wiki/pages/"
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

@test "WIKI-006: All agents write to wiki/pages/ not wiki/entries/" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        # Skip Librarian and Guide, ROSTER, README
        case "$filename" in
            Librarian.md|Guide.md|ROSTER.md|README.md) continue ;;
        esac
        if grep -q "wiki/entries/" "$file"; then
            echo "FAIL: $filename still references wiki/entries/ instead of wiki/pages/"
            return 1
        fi
    done
}

@test "WIKI-007: All agents with session save write to wiki/pages/" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        case "$filename" in
            Librarian.md|Guide.md|ROSTER.md|README.md) continue ;;
        esac
        if grep -q "会话保存规范" "$file"; then
            grep -q "wiki/pages/" "$file" || {
                echo "FAIL: $filename has session save but does not reference wiki/pages/"
                return 1
            }
        fi
    done
}

@test "WIKI-008: All agents with session save use YAML frontmatter format" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        case "$filename" in
            Librarian.md|Guide.md|ROSTER.md|README.md) continue ;;
        esac
        if grep -q "会话保存规范" "$file"; then
            grep -q "type:" "$file" || {
                echo "FAIL: $filename session save does not include 'type:' frontmatter field"
                return 1
            }
        fi
    done
}

@test "WIKI-009: All agents with session save use wikilink syntax" {
    for file in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$file")
        case "$filename" in
            Librarian.md|Guide.md|ROSTER.md|README.md) continue ;;
        esac
        if grep -q "会话保存规范" "$file"; then
            grep -qE "\[\[.*\]\]" "$file" || {
                echo "FAIL: $filename session save does not mention [[wikilink]] syntax"
                return 1
            }
        fi
    done
}

@test "WIKI-010: Guide references wiki/index.md for queries" {
    run grep -qE "wiki/index\.md" "$AGENTS_DIR/Guide.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Guide.md does not reference wiki/index.md for queries"
        false
    }
}
