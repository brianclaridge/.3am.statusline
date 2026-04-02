"""Build atomic display tokens from stdin JSON and git data."""
from __future__ import annotations

from config import CONFIG, RESET
from render import c, format_cost, format_duration, format_relative_time, format_token_count, link, render_bar, tier_color

_DEFAULTS = CONFIG.get("defaults", {})


def build_tokens(
    data: dict,
    config: dict,
    git_data: dict,
    plan_info: dict | None = None,
) -> dict[str, str]:
    """Build all tokens as atomic ANSI strings. Dim defaults when absent/zero."""
    colors = config.get("colors", {})
    labels = config.get("labels", {})
    dim = colors.get("dim", "2")
    tokens: dict[str, str] = {}

    # Structural space token -- raw, not ANSI-wrapped
    tokens["s"] = config.get("space_character", " ")

    def dim_default(key: str) -> str:
        text = _DEFAULTS.get(key, "")
        return f"{c(dim)}{text}{RESET}" if text else ""

    # -- 1. model / cost / duration / lines --

    model_data = data.get("model", {})
    display_name = model_data.get("display_name", "?")
    mc = colors.get("model", "1;36")
    tokens["model_name"] = f"{c(mc)}{display_name}{RESET}"

    cost_data = data.get("cost", {})
    duration_ms = cost_data.get("total_duration_ms", 0)
    dc = colors.get("duration", "37")
    tokens["duration"] = (
        f"{c(dc)}{format_duration(duration_ms)}{RESET}"
        if duration_ms > 0 else dim_default("duration")
    )

    total_cost = cost_data.get("total_cost_usd", 0)
    costc = colors.get("cost", "1;37")
    tokens["cost"] = f"{c(costc)}${total_cost:.2f}{RESET}"

    lines_added = cost_data.get("total_lines_added", 0)
    lines_removed = cost_data.get("total_lines_removed", 0)
    ac = colors.get("added", "1;32")
    rc = colors.get("removed", "1;31")
    tokens["lines_added"] = f"{c(ac)}+{lines_added}{RESET}" if lines_added else dim_default("lines_added")
    tokens["lines_removed"] = f"{c(rc)}-{lines_removed}{RESET}" if lines_removed else dim_default("lines_removed")

    # separator
    sep_str = labels.get("sep", "\u2502")
    sepc = colors.get("sep", "90")
    tokens["sep"] = f"{c(sepc)}{sep_str}{RESET}"

    # -- session_id --

    session_id = data.get("session_id", "")
    sidc = colors.get("session_id", dim)
    tokens["session_id"] = f"{c(sidc)}{session_id}{RESET}" if session_id else dim_default("session_id")
    tokens["session_id_short"] = f"{c(sidc)}{session_id[:8]}{RESET}" if session_id else dim_default("session_id")

    # -- session_name --

    session_name = data.get("session_name", "")
    snc = colors.get("session_name", dim)
    tokens["session_name"] = f"{c(snc)}{session_name}{RESET}" if session_name else dim_default("session_name")

    # -- api duration --

    api_ms = cost_data.get("total_api_duration_ms", 0)
    adc = colors.get("api_duration", dim)
    tokens["api_duration"] = (
        f"{c(adc)}{format_duration(api_ms)}{RESET}"
        if api_ms > 0 else dim_default("api_duration")
    )

    # -- version / output style --

    version = data.get("version", "")
    vc = colors.get("version", dim)
    tokens["version"] = f"{c(vc)}v{version}{RESET}" if version else dim_default("version")

    style_name = data.get("output_style", {}).get("name", "")
    tokens["output_style"] = f"{c(dim)}{style_name}{RESET}" if style_name else dim_default("output_style")

    # -- theme --

    theme_name = config.get("theme", "")
    thc = colors.get("theme", dim)
    tokens["theme"] = f"{c(thc)}{theme_name}{RESET}" if theme_name else dim_default("theme")

    # -- 2. context --

    ctx = data.get("context_window", {})
    ctx_pct = ctx.get("used_percentage", 0)
    cc = tier_color(ctx_pct, "context")
    tokens["context_bar"] = f"{c(cc)}{render_bar(ctx_pct / 100)}{RESET}"
    tokens["context_pct"] = f"{c(cc)}{ctx_pct:.0f}%{RESET}"

    # -- token counts --

    total_in = ctx.get("total_input_tokens", 0)
    total_out = ctx.get("total_output_tokens", 0)
    context_used = total_in + total_out
    tokens["context_used"] = f"{c(cc)}{format_token_count(context_used)}{RESET}" if context_used else dim_default("context_used")
    current = ctx.get("current_usage", {})
    cache_read = current.get("cache_read_input_tokens", 0)

    tic = colors.get("tokens_in", dim)
    toc = colors.get("tokens_out", dim)
    cac = colors.get("cache", dim)
    tokens["total_input"] = f"{c(tic)}{format_token_count(total_in)}\u2193{RESET}" if total_in else dim_default("total_input")
    tokens["total_output"] = f"{c(toc)}{format_token_count(total_out)}\u2191{RESET}" if total_out else dim_default("total_output")
    tokens["cache_read"] = f"{c(cac)}{format_token_count(cache_read)}\u27F3{RESET}" if cache_read else dim_default("cache_read")

    # -- exceeds 200k warning --

    exc = colors.get("exceeds_200k", colors.get("context_crit", "1;31"))
    tokens["exceeds_200k"] = (
        f"{c(exc)}\u26A0 200k+{RESET}"
        if data.get("exceeds_200k_tokens") else dim_default("exceeds_200k")
    )

    # -- remaining percentage --

    remaining_pct = ctx.get("remaining_percentage", 0)
    tokens["remaining_pct"] = f"{c(cc)}{remaining_pct}% free{RESET}"

    # -- rate limits --

    rate_data = data.get("rate_limits", {})
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        window = rate_data.get(key, {})
        pct = window.get("used_percentage")
        resets_at = window.get("resets_at")
        if pct is not None:
            rc = tier_color(pct, "rate")
            tokens[f"rate_{label}_pct"] = f"{c(rc)}{pct:.0f}%{RESET}"
            tokens[f"rate_{label}_bar"] = f"{c(rc)}{render_bar(pct / 100)}{RESET}"
        else:
            tokens[f"rate_{label}_pct"] = dim_default(f"rate_{label}_pct")
            tokens[f"rate_{label}_bar"] = dim_default(f"rate_{label}_bar")
        if resets_at is not None:
            rstc = colors.get("rate_reset", dim)
            tokens[f"rate_{label}_reset"] = f"{c(rstc)}{format_relative_time(resets_at)}{RESET}"
        else:
            tokens[f"rate_{label}_reset"] = dim_default(f"rate_{label}_reset")

    # -- path display helpers --

    def _unix_path(p: str) -> str:
        """Convert any path to Unix-style: D:\\foo\\bar -> /d/foo/bar."""
        p = p.replace("\\", "/")
        # Windows drive letter: C:/foo -> /c/foo
        if len(p) >= 2 and p[1] == ":":
            p = "/" + p[0].lower() + p[2:]
        return p

    def _relative_or_unix(child: str, parent: str) -> str:
        """Show child relative to parent: ./sub, ../sibling, or full Unix-style."""
        import posixpath
        uc = _unix_path(child)
        up = _unix_path(parent)
        # Only compute relative if same root (both /d/... or both /home/...)
        uc_parts = uc.strip("/").split("/")
        up_parts = up.strip("/").split("/")
        if not up or not uc_parts or not up_parts or uc_parts[0] != up_parts[0]:
            return uc
        rel = posixpath.relpath(uc, up)
        if rel == ".":
            return uc
        if not rel.startswith(".."):
            return "./" + rel
        return rel

    # -- cwd --

    cwd_raw = data.get("cwd", "")
    project_dir = data.get("workspace", {}).get("project_dir", "")
    cwdc = colors.get("cwd", dim)
    if cwd_raw:
        cwd_display = _relative_or_unix(cwd_raw, project_dir) if project_dir else _unix_path(cwd_raw)
        tokens["cwd"] = f"{c(cwdc)}{cwd_display}{RESET}"
    else:
        tokens["cwd"] = dim_default("cwd")

    # -- project_dir --

    pdc = colors.get("project_dir", dim)
    tokens["project_dir"] = f"{c(pdc)}{_unix_path(project_dir)}{RESET}" if project_dir else dim_default("project_dir")

    # -- transcript path --

    transcript_path = data.get("transcript_path", "")
    tpc = colors.get("transcript_path", dim)
    tokens["transcript_path"] = f"{c(tpc)}{transcript_path}{RESET}" if transcript_path else dim_default("transcript_path")

    # -- workspace directories --

    ws = data.get("workspace", {})
    current_dir = ws.get("current_dir", "")
    cdc = colors.get("current_dir", dim)
    if current_dir:
        cd_display = _relative_or_unix(current_dir, project_dir) if project_dir else _unix_path(current_dir)
        tokens["current_dir"] = f"{c(cdc)}{cd_display}{RESET}"
    else:
        tokens["current_dir"] = dim_default("current_dir")

    added_dirs = ws.get("added_dirs", [])
    adc2 = colors.get("added_dirs", dim)
    added_str = ", ".join(added_dirs) if isinstance(added_dirs, list) else str(added_dirs)
    tokens["added_dirs"] = f"{c(adc2)}{added_str}{RESET}" if added_dirs else dim_default("added_dirs")

    # -- context window size --

    ctx_size = ctx.get("context_window_size", 0)
    cwsc = colors.get("context_window_size", dim)
    tokens["context_window_size"] = f"{c(cwsc)}{format_token_count(ctx_size)}{RESET}" if ctx_size else dim_default("context_window_size")

    # -- current turn token counts --

    turn_in = current.get("input_tokens", 0)
    turn_out = current.get("output_tokens", 0)
    cache_create = current.get("cache_creation_input_tokens", 0)

    tic2 = colors.get("turn_input", dim)
    toc2 = colors.get("turn_output", dim)
    ccc = colors.get("cache_creation", dim)
    tokens["turn_input"] = f"{c(tic2)}{format_token_count(turn_in)}\u2193{RESET}" if turn_in else dim_default("turn_input")
    tokens["turn_output"] = f"{c(toc2)}{format_token_count(turn_out)}\u2191{RESET}" if turn_out else dim_default("turn_output")
    tokens["cache_creation"] = f"{c(ccc)}{format_token_count(cache_create)}\u270E{RESET}" if cache_create else dim_default("cache_creation")

    # -- model id --

    model_id = model_data.get("id", "")
    mic = colors.get("model_id", dim)
    tokens["model_id"] = f"{c(mic)}{model_id}{RESET}" if model_id else dim_default("model_id")

    # -- plan (from filesystem) --

    pi = plan_info or {}
    plan_slug = pi.get("slug", "")
    plan_title = pi.get("title", "")
    plc = colors.get("plan", dim)
    ptc = colors.get("plan_title", dim)
    tokens["plan"] = f"{c(plc)}{plan_slug}{RESET}" if plan_slug else dim_default("plan")
    tokens["plan_title"] = f"{c(ptc)}{plan_title}{RESET}" if plan_title else dim_default("plan_title")

    # -- 3. git --

    git = git_data or {}

    remote_url = git.get("remote_url", "")
    ruc = colors.get("repo_url", dim)
    tokens["repo_url"] = f"{c(ruc)}{link(remote_url, remote_url)}{RESET}" if remote_url else dim_default("repo_url")

    branch = git.get("branch", "")
    sha = git.get("sha", "")
    is_github = "github" in remote_url
    path_sep = "/" if is_github else "/-/"
    if branch:
        bc = colors.get("git_branch", "1;36")
        if remote_url:
            branch_url = f"{remote_url}{path_sep}tree/{branch}"
            tokens["git_branch"] = f"{c(bc)}{link(branch_url, branch)}{RESET}"
        else:
            tokens["git_branch"] = f"{c(bc)}{branch}{RESET}"

        shc = colors.get("git_sha", "2")
        if sha and remote_url:
            commit_url = f"{remote_url}{path_sep}commit/{sha}"
            tokens["git_sha"] = f"{c(shc)}{link(commit_url, sha)}{RESET}"
        elif sha:
            tokens["git_sha"] = f"{c(shc)}{sha}{RESET}"
        else:
            tokens["git_sha"] = dim_default("git_sha")

        if git.get("dirty"):
            dtyc = colors.get("git_dirty", "1;33")
            tokens["git_dirty"] = f"{c(dtyc)}\u25cf{RESET}"
        else:
            gc = colors.get("git_clean", "1;32")
            tokens["git_dirty"] = f"{c(gc)}\u2714{RESET}"

        staged = git.get("staged", 0)
        stc = colors.get("git_staged", "1;32")
        tokens["git_staged"] = f"{c(stc)}+{staged}{RESET}" if staged else dim_default("git_staged")

        unstaged = git.get("unstaged", 0)
        usc = colors.get("git_unstaged", "1;33")
        tokens["git_unstaged"] = f"{c(usc)}~{unstaged}{RESET}" if unstaged else dim_default("git_unstaged")

        untracked = git.get("untracked", 0)
        utc = colors.get("git_untracked", "2")
        tokens["git_untracked"] = f"{c(utc)}?{untracked}{RESET}" if untracked else dim_default("git_untracked")

        ahead = git.get("ahead", 0)
        ahc = colors.get("git_ahead", "1;32")
        tokens["git_ahead"] = f"{c(ahc)}{ahead}\u2191{RESET}" if ahead else dim_default("git_ahead")

        behind = git.get("behind", 0)
        bhc = colors.get("git_behind", "1;31")
        tokens["git_behind"] = f"{c(bhc)}{behind}\u2193{RESET}" if behind else dim_default("git_behind")
    else:
        for k in ("git_branch", "git_sha", "git_dirty", "git_staged", "git_unstaged", "git_untracked", "git_ahead", "git_behind"):
            tokens[k] = dim_default(k)

    return tokens
