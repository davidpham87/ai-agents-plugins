# Harness Directives Plugin

Skeleton Antigravity (`agy`) plugin for collecting your harness skills,
rules, and directives in one versioned repository.

## Structure

```text
.
├── plugin.json                 # Plugin manifest (required)
├── rules/
│   └── AGENTS.md               # Always-on rules and directives
└── skills/
    └── example-skill/
        └── SKILL.md            # On-demand skill template
```

Optional files you can add at the root when needed:

- `hooks.json` for lifecycle hooks
- `mcp_config.json` for MCP server integrations

## Adding Customizations

- **Rules and directives**: Edit `rules/AGENTS.md`. Keep it concise;
  each rule file is capped at 24,000 bytes.
- **Skills**: Copy `skills/example-skill/` to `skills/<skill-name>/` and
  update `SKILL.md` frontmatter (`name` and `description`) and steps.

## Validate and Install

Validate the plugin structure with the Antigravity CLI:

```sh
agy plugin validate . --strict
```

Install the plugin locally:

```sh
agy plugin install .
```
