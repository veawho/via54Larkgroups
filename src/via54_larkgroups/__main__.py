"""Main CLI entry point for feishu-vault.

Usage:
  feishu-vault config --app-id ... --app-secret ...    # save OAuth app credentials
  feishu-vault login                                    # OAuth browser flow
  feishu-vault status                                   # show current state
  feishu-vault sync [--include-attachments]            # pull last 24h
  feishu-vault archive [--date YYYY-MM-DD]              # export to markdown
  feishu-vault search KEYWORD                           # search archived md files
  feishu-vault --enable-auto-sync                       # enable daily background sync
  feishu-vault stop                                     # stop background sync (5s)
  feishu-vault logout                                   # clear token
"""
import argparse
import json
import os
import sys
import time

# Ensure the package is importable when run as script
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from via54_larkgroups import config, oauth, sync, archive as archive_mod


def cmd_config(args):
    config.ensure_dirs()
    cfg = {}
    if config.CONFIG_FILE.exists():
        try:
            with open(config.CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except json.JSONDecodeError:
            cfg = {}
    if args.app_id:
        cfg["app_id"] = args.app_id
    if args.app_secret:
        cfg["app_secret"] = args.app_secret
    if not cfg.get("app_id") or not cfg.get("app_secret"):
        print("[feishu-vault] Need both --app-id and --app-secret")
        return 2
    with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("[feishu-vault] Saved app_id + app_secret to " + str(config.CONFIG_FILE))
    print("[feishu-vault] NOTE: file contains secret. Do not commit to git.")
    config.write_audit("config_updated")
    return 0


def cmd_login(args):
    if not config.CONFIG_FILE.exists():
        print("[feishu-vault] Run `feishu-vault config --app-id ... --app-secret ...` first")
        return 2
    with open(config.CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    try:
        token = oauth.login(cfg["app_id"], cfg["app_secret"])
    except Exception as e:
        print("[feishu-vault] Login failed: " + str(e))
        return 1
    print("[feishu-vault] Login OK. Token expires at " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(token["expires_at"])) +
          " (24h max).")
    return 0


def cmd_status(args):
    config.ensure_dirs()
    print("=== feishu-vault status ===")
    print("Data root: " + str(config.DATA_ROOT))
    print("Config file: " + ("present" if config.CONFIG_FILE.exists() else "MISSING (run `config`)"))
    token = oauth.load_token()
    if token:
        remaining = token["expires_at"] - int(time.time())
        print("Token: present, expires in " + str(remaining // 3600) + "h " +
              str((remaining % 3600) // 60) + "m")
        print("Scopes: " + token.get("scope", "<unset>"))
    else:
        print("Token: NONE (run `login` or token expired)")
    if config.AUTO_SYNC_FLAG.exists():
        print("Auto-sync: ENABLED (touch data root/auto_sync.enabled exists)")
    else:
        print("Auto-sync: OFF (default)")
    if config.VAULT_DB.exists():
        import sqlite3
        c = sqlite3.connect(str(config.VAULT_DB))
        msg_count = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        chat_count = c.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        att_count = c.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]
        c.close()
        print("DB: " + str(msg_count) + " messages, " + str(chat_count) +
              " chats, " + str(att_count) + " attachments")
    else:
        print("DB: not initialized (run `sync` first)")
    return 0


def cmd_sync(args):
    token = oauth.load_token()
    if not token:
        print("[feishu-vault] No valid token. Run `login` first.")
        return 2
    include_att = bool(args.include_attachments)
    if include_att:
        print("[feishu-vault] WARNING: --include-attachments will DOWNLOAD files to disk.")
        print("[feishu-vault] This includes images, audio, video, documents. Press Ctrl-C in 5s to abort.")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("Aborted.")
            return 1

    def progress(msg):
        print("[feishu-vault] " + msg)

    print("[feishu-vault] Syncing last 24h...")
    stats = sync.sync_today(token, include_attachments=include_att, progress=progress)
    print("[feishu-vault] Done: " + json.dumps(stats))
    return 0


def cmd_archive(args):
    target = None
    if args.date:
        import datetime
        target = datetime.date.fromisoformat(args.date)
    result = archive_mod.archive_day(target_date=target)
    print("[feishu-vault] Wrote " + result["md_path"])
    print("[feishu-vault]   " + str(result["messages"]) + " messages, " +
          str(result["chats"]) + " chats")
    return 0


def cmd_search(args):
    keyword = args.keyword
    if not keyword:
        print("[feishu-vault] Need --keyword")
        return 2
    matches = []
    for md in config.ARCHIVE_DIR.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if keyword in text:
            matches.append(str(md))
    print("[feishu-vault] Found in " + str(len(matches)) + " files:")
    for m in matches:
        print("  " + m)
    return 0


def cmd_enable_auto_sync(args):
    config.ensure_dirs()
    config.AUTO_SYNC_FLAG.touch()
    print("[feishu-vault] Auto-sync ENABLED. Touch " + str(config.AUTO_SYNC_FLAG) +
          " to check; remove it to disable.")
    config.write_audit("auto_sync_enabled")
    return 0


def cmd_stop(args):
    config.SYNC_STOP_FILE.touch()
    if config.AUTO_SYNC_FLAG.exists():
        config.AUTO_SYNC_FLAG.unlink()
    print("[feishu-vault] Stop signal sent. Background sync will exit within 5s.")
    config.write_audit("user_stop")
    return 0


def cmd_logout(args):
    oauth.clear_token()
    print("[feishu-vault] Token cleared. Next `sync` requires `login`.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="feishu-vault",
        description="Local-only Feishu (Lark) chat archive tool",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cfg = sub.add_parser("config", help="save OAuth app credentials")
    p_cfg.add_argument("--app-id", required=True)
    p_cfg.add_argument("--app-secret", required=True)
    p_cfg.set_defaults(func=cmd_config)

    p_login = sub.add_parser("login", help="OAuth browser login")
    p_login.set_defaults(func=cmd_login)

    p_status = sub.add_parser("status", help="show current state")
    p_status.set_defaults(func=cmd_status)

    p_sync = sub.add_parser("sync", help="pull last 24h of messages")
    p_sync.add_argument("--include-attachments", action="store_true",
                        help="DOWNLOAD attachment files (default: metadata only)")
    p_sync.set_defaults(func=cmd_sync)

    p_arch = sub.add_parser("archive", help="export to markdown")
    p_arch.add_argument("--date", help="YYYY-MM-DD, default today")
    p_arch.set_defaults(func=cmd_archive)

    p_srch = sub.add_parser("search", help="search keyword in archive")
    p_srch.add_argument("--keyword", required=True)
    p_srch.set_defaults(func=cmd_search)

    p_stop = sub.add_parser("stop", help="stop background sync (5s)")
    p_stop.set_defaults(func=cmd_stop)

    p_lo = sub.add_parser("logout", help="clear saved token")
    p_lo.set_defaults(func=cmd_logout)

    # Top-level flag handled manually BEFORE argparse to avoid subparser conflict
    if argv is None:
        argv = sys.argv[1:]
    if "--enable-auto-sync" in argv:
        return cmd_enable_auto_sync(argparse.Namespace(enable_auto_sync=True))

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())