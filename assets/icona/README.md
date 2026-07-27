# Drops — macOS App Icon

## Files
- **Drops-1024.png** — 1024×1024 master
- **Drops-512.png**  — 512×512
- **Drops.iconset/** — all sizes Apple needs for an .icns
- **build-icns.sh**  — one-shot script to produce Drops.icns

## To build Drops.icns (macOS)

```bash
bash build-icns.sh
```

This renames the @2x files (they're shipped as *-2x.png because the
generator's filesystem doesn't allow @ in filenames) and runs
`iconutil -c icns Drops.iconset -o Drops.icns`.

Drop the resulting **Drops.icns** into your app bundle's
`Contents/Resources/` and reference it from `Info.plist` as
`CFBundleIconFile`.

## Brand
- Primary:   `#22c55e`
- Surface:   `#0a0a0a`
- Accent:    `#f0f0f0`
- Shape:     macOS squircle (superellipse), ~22% radius
