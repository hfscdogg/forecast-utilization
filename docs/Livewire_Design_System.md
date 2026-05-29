# Livewire Design System

> Brand foundations and the Email Marketing Best Practices framework (v3.0, April 2026).
> Use this file as a reference doc or `CLAUDE.md` in Claude Code so generated work stays on-brand.
> Maintained by Demand Growth Partner.

---

## 1. Brand Foundations

### 1.1 Typography

Two families. Fraunces for display/editorial, Montserrat for everything else.

| Role | Family | Notes |
|---|---|---|
| Display / headlines | **Fraunces** (serif) | `font-variation-settings: "opsz" 144, "SOFT" 50;` letter-spacing `-0.02em`, line-height `~0.98`. Use italic + lighter weight for accent words. |
| Body / UI / labels | **Montserrat** (sans) | Weights 100–900 available. Body copy at 400–500; labels/eyebrows at 600. Base letter-spacing `-0.005em`. |
| Code / specs / monospace | JetBrains Mono | Optional. Used for numeric tokens, hex values, blueprint indices. |

**Eyebrow style:** 10.5px, `letter-spacing: 0.24em`, uppercase, weight 600, copper accent color.

Font files live in `fonts/` (Montserrat full family) and Fraunces loads from Google Fonts. When starting a new project, upload these via the org Brand Kit so they're inherited automatically.

### 1.2 Color Tokens

These are the UI / web tokens for Livewire surfaces (dark editorial aesthetic).

#### Ink (neutrals, dark)
| Token | Hex |
|---|---|
| `ink-950` | `#0B0B09` |
| `ink-900` | `#12120F` |
| `ink-800` | `#1C1C18` |
| `ink-700` | `#2A2A24` |
| `ink-600` | `#3A3A33` |
| `ink-500` | `#5B5B52` |
| `ink-400` | `#85857A` |
| `ink-300` | `#B0B0A4` |
| `ink-200` | `#D8D6CC` |

#### Bone / Cream (light surfaces & text)
| Token | Hex |
|---|---|
| `bone-50` | `#FAF8F2` |
| `bone-100` | `#F4F0E8` |
| `bone-200` | `#ECE6D9` |
| `bone-300` | `#DFD7C5` |
| `cream` | `#F5EFE6` |

#### Copper / Orange (brand accent)
| Token | Hex | Use |
|---|---|---|
| `copper-50` | `#FBEBD8` | Soft tint backgrounds on light |
| `copper-100` | `#F9D5AE` | Tint |
| `copper-300` | `#F6A85F` | Accent text on dark, hover |
| `copper-500` | `#F08223` | Primary CTA (web UI) |
| `copper-600` | `#D46C13` | CTA hover |
| `copper-700` / `text-safe` | `#A85200` | **Orange text/links on light backgrounds (WCAG AA safe)** |
| Livewire Orange | `#F7941D` | **Email brand orange** — buttons, eyebrows on dark (passes AAA on dark, FAILS on light) |

**Accent rule:** `#F7941D` on light backgrounds fails contrast — always use `#A85200` for orange text/links on white or cream. On dark, use `#F7941D` freely.

### 1.3 Logos

Files in `assets/`:
- `logo-horizontal-white.png` — **correct for dark nav bars and footers.**
- `logo-horizontal-black.png` — for light backgrounds.
- `logo-horizontal-orange.png` — accent contexts.
- `logo-mark-white.png`, `logo-mark-orange.png` — swoosh mark only. **Not a substitute for the wordmark** in email nav bars.

### 1.4 Voice & Aesthetic

Confident, warm, practical, never salesy. Dark editorial surfaces, warm cream for consumer-facing content, copper accent used sparingly. Avoid gradients-as-decoration, emoji (except social), and generic SaaS tropes. Specific over vague.

---

## 2. Email Marketing Best Practices (v3.0)

> Binding for: Henry-voiced newsletters, specifier/partner emails, Johnson Controls conquest sends, promotional launches.

### 2.1 What the Research Says

**Subject lines** (highest-leverage element — determines open rate):
- 30–40 characters (6–8 words). Over 50 is clipped on mobile (60%+ of the list opens on mobile).
- Skepticism-based hooks beat generic statements for specifier audiences.
- Question formats outperform statements by 10–15% in B2C luxury.
- Personalization tokens lift opens 5–10% with clean list data.
- Avoid spam triggers: `free`, `guaranteed`, `act now`, `limited time`, `exclusive offer`.
- Preheader is the second subject line: extend, never repeat. 85–100 characters ideal.
- **No emojis** — render inconsistently across Outlook/older Android, dilute professionalism.

**Above the fold** (first 300–400px; readers decide in ~9 seconds):
- Specifier promos → hero image with baked-in text. Newsletters → display-first typographic hero.
- Lead with content, never a logo banner + white space.
- Specifier trust signal = product experience. Newsletter trust signal = Henry's name/face.

**Navigator blocks** (new, April 2026) — for newsletters with 2+ stories:
- Short card-based table of contents right after the hero; cards link to anchors below.
- Reduces perceived length, respects reader time, gives each story an entry point.
- 2–3 cards max. Each: numbered index (01, 02), short eyebrow label, serif headline, one-sentence description. Tappable.

**Video thumbnails:**
- 200–300% more clicks than text-only (HubSpot, Wistia).
- Play button **baked into the JPG via Python/Pillow** — CSS `position:absolute` overlays break in Outlook/Gmail.
- Place immediately after hero, same dark background, before first CTA.
- Never reference the same video in both the baked image and the copy.
- Two videos → Video 1 is the primary thumbnail; Video 2 is a text link or dropped.
- ≤90 seconds converts better.

**CTAs & conversion:**
- Single-primary-CTA emails outperform multi-CTA by up to 371% CTR.
- Primary CTA appears ≥3 times: top/early, mid, bottom.
- Copy = action + outcome ("Reserve Your Visit" > "Book Now"/"Learn More").
- Microcopy below CTA reduces anxiety ("Free. No signup. Takes about a minute.").
- Inline CTA cards save vertical space vs. full-width blocks — use for secondary/within-story CTAs; reserve full-width for the top conversion action.
- Offers/credits go just before booking options, not at the end.

**FAQ accordions do NOT work in email (technical constraint):** email clients strip the JS. A `+` icon that doesn't expand is worse than plain Q/A. **Always show FAQ answers inline.**

**Offers & promotions:** frame as client benefits, not hooks. Plain declarative language. No countdown/urgency/exclamation for professional audiences. Place offer inside the dark booking section, between heading and Option A.

**Images:** all hosted at `stratus.campaign-image.com` (no exceptions). `object-fit:cover`/`object-position` unsupported in Outlook — use explicit height to control crop. White wordmark logo on dark nav. YouTube auto-thumb format `https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg`. Images with white frames/borders must sit on white or cream sections (dark exposes the border).

**Social proof:** review counts + ratings lift click-to-consult 15–25% in home services. Trust strip (**20+ years · 4.9 stars / 421 reviews · 80% referrals · Lutron Certified**) appears early, right after the first CTA block. Named technicians are unusually powerful for Livewire.

### 2.2 Structure Blueprints

#### Standard Newsletter (updated April 2026) — default for monthly Henry-voiced sends
| # | Block | Background | Purpose |
|---|---|---|---|
| 01 | Nav Bar | Charcoal `#1A1A1A` | Logo left, issue badge right. 16px padding. |
| 02 | Hero | Deep Black `#0D0D0D` | Eyebrow + "From Henry Clifford", display serif 44px. Text only, no photo. |
| 03 | Navigator | Charcoal `#1A1A1A` | 2–3 tappable cards linking to stories below. |
| 04 | Body + Visual | Cream `#F5EFE6` | Henry's letter, short paragraphs. Primary visual here. |
| 05 | Inline CTA | Cream `#F5EFE6` | White rounded card, headline + button + microcopy. |
| 06 | Feature / Event | Charcoal `#1A1A1A` | Second story with its own image and primary CTA. |
| 07 | Trust Strip | Warm Grey `#FAFAF9` | Same three stats every time. |
| 08 | FAQ | Warm Grey `#FAFAF9` | 4–6 plain Q/A. No fake accordion icons. |
| 09 | Footer | Deep Black `#0D0D0D` | Logo + social only. Zoho auto-appends compliance block. |

#### Specifier / Partner (Ketra Experience Center build, April 2026)
| # | Block | Background | Purpose |
|---|---|---|---|
| 01 | Nav Bar | `#1A1A1A` | Logo left, campaign badge right. |
| 02 | Hero Image | `#0D0D0D` | Flat JPG: room photo + gradient + headline + CTA baked via Pillow. |
| 03 | Transition Bar | `#0D0D0D` | Bridge copy. Never repeat hero text. |
| 04 | Video Thumbnail | `#0D0D0D` | Flat JPG, baked play button, links to YouTube. |
| 05 | Primary CTA | `#0D0D0D` | Reserve Your Visit + microcopy after video. |
| 06 | Trust Strip | `#FAFAF9` | 20+ years, 4.9 stars, 80% referrals, Lutron Certified. |
| 07 | What Is [Product] | `#FFFFFF` | Plain-language, 2 short paragraphs. |
| 08 | Room Image | Full bleed | Crop to show architecture and light. |
| 09 | What to Expect | `#FAFAF9` | Numbered 01–04 steps. |
| 10 | Lifestyle Image 2 | Full bleed | Dusk/warm scene. Italic caption below. |
| 11 | Booking Options | `#1A1A1A` | Heading + offer/credit + Option A (orange) + Option B (ghost). |
| 12 | Aspirational Image | Full bleed | Premium room/project photo. |
| 13 | Who This Is For | `#FFFFFF` | Specifier types with orange dot markers. |
| 14 | Final CTA | Deep Charcoal `#111111` | Closing statement + Reserve button + phone number. |
| 15 | Footer | `#0D0D0D` | Logo, social only. |

### 2.3 Email Color System (v3)

| Hex | Name | Use |
|---|---|---|
| `#0D0D0D` | Deep Black | Hero blocks, deepest footer. Highest contrast, display headlines. |
| `#111111` | Deep Charcoal | Final CTA close. Slight lift off deep black for rhythm. |
| `#1A1A1A` | Charcoal | Nav bar, navigator, feature blocks. Main dark. |
| `#F5EFE6` | Warm Cream | Newsletter body. Default for Henry-voiced newsletters (April 2026+). |
| `#FAFAF9` | Warm Grey | Trust strip & FAQ. Light without pure-white glare. |
| `#FFFFFF` | Pure White | Specifier body; inline CTA cards inside cream sections. |

**Cream vs. white:** Cream = newsletters / consumer / warm editorial. White = specifier / conquest / corporate (and inline CTA cards on cream). Pure white with no cream reads more corporate; avoid for newsletters unless called for.

**Text color:** all pairings meet WCAG AA. `#F7941D` fails on light → use `#A85200` for text links/small labels on white/cream. `#F7941D` passes AAA on dark — use freely. Full contrast table: *Livewire ADA Accessibility Standards* doc.

### 2.4 Subject Line Framework

Every subject must satisfy **at least 3 of 5**:
1. Opens a question/loop the reader wants to close.
2. Speaks to a specific felt experience, not a feature.
3. Under 40 characters.
4. Could plausibly be from a trusted neighbor/peer, not a brand.
5. Pairs with a preheader that extends, not repeats.

**Approved patterns:**
- Skepticism hook: "They came in skeptical. Watch what happened."
- Problem-first: "Your home looks finished. Why doesn't it feel finished?"
- Outcome-first: "What great lighting actually changes"
- Curiosity gap: "The one thing most finished homes are missing"
- Seasonal invitation: "Spring is here. Come outside with us."
- Two-word punch: "First impressions. Unfiltered."

**Hard rules:** No emojis. No em dashes. ≤40 characters. The subject never carries both the *what* and the *why* — use the preheader to extend.

### 2.5 Voice Rules

**Always:**
- Short paragraphs, max 3 lines.
- Specific over vague ("421 reviews at 4.9 stars", not "highly rated").
- Bold one key phrase per section for scanners.
- End the letter with a direct invitation, not a soft close.
- Use "we" throughout — a team, not a company.
- Frame offers as client benefits ("A note for your next client conversation").

**Never:**
- Em dashes (use commas/semicolons/shorter sentences).
- Exclamation points in body copy (social only).
- Vague superlatives: innovative, cutting-edge, world-class, best-in-class.
- Fear-based language ("don't get left behind", "before it's too late").
- Standalone corporate nouns: solutions, synergy, seamless (without specifics).
- Countdown/urgency for professional audiences.
- Emojis in subject lines or body (social only).

### 2.6 Technical Production Rules

**HTML structure:**
- Table-based layouts only. No flexbox/grid.
- 600px max-width container, centered, background color on `body`.
- Single column only.
- All inline styles. No external stylesheets.
- `line-height:0` and `font-size:0` on image container cells to kill ghost spacing.

**Vertical spacing (v3 — leadership asked for screen efficiency):**
- Nav bar: 16px vertical (was 20px).
- Hero: 40px top/bottom (was 52px).
- Body section: 40–48px by content weight (was 48px).
- Footer: 36px top, 32px bottom (was 44px).
- Reduce gaps 8–12px between stacked same-background sections.

**Buttons:**
- Wrap in `table > tr > td`, not a `div`.
- Declare color on all 5 link pseudo-classes with `!important`.
- ≥44px tall (mobile tap target).
- Pill: `border-radius:30px`.
- Primary: bg `#F7941D`, border `2px solid #F7941D`, white text.
- Ghost on dark: transparent, border `2px solid rgba(255,255,255,.35)`, white text.

**Inline CTA cards (v3):** white card `border-radius:10px` inside cream/light section; serif headline ~20px; centered orange pill button; microcopy ~12px grey; ~28px padding. Saves 60–80px vs. full-width block.

**Images:** hosted at `stratus.campaign-image.com`; descriptive `alt` on every tag; `width:100%`; explicit heights for crop (no `object-position`); baked play buttons via Pillow; white-bordered images on white/cream sections only.

**Hero image with baked-in text (Pillow method):**
1. Download source from `stratus.campaign-image.com`.
2. Resize/crop to 600px wide using `Image.LANCZOS`.
3. Directional dark gradient overlay (stronger left, lighter right) via RGBA compositing.
4. Render eyebrow/headline/subline/pill button with `ImageDraw` (DejaVu or Liberation fonts).
5. Save JPG at quality 92–93, upload to Zoho Campaigns image library.
6. Use the resulting stratus URL as a single linked `<img>` — the whole image is the clickable CTA.

**Zoho Campaigns:**
- Zoho auto-appends compliance footer (sender info, address, unsubscribe, preferences, privacy, terms). Do not duplicate in HTML footer.
- Custom HTML footer: Livewire logo + social links only.
- CRM sync: `Contacts › Sync Services › New Sync` → Leads module.
- Email Opt-out toggle needs an Email Opt-out field on CRM Leads module — flag for Solomon if missing.
- Test-send to self before deploying. Confirm images load and links active.
- Public stratus URLs only generate when an image renders in a live campaign or preview send.

### 2.7 Performance Benchmarks

| Metric | Industry Avg | Livewire Target |
|---|---|---|
| Open Rate | 19–23% | ≥ 25% |
| Click-Through Rate | 2.0–3.5% | ≥ 4.0% |
| Click-to-Open Rate | 10–15% | ≥ 18% |
| Unsubscribe Rate | < 0.5% | < 0.3% |
| Booking Conversion | — | Track monthly |

### 2.8 Pre-Send Checklist

**Subject & preheader:** <40 chars · no emojis · opens question/hook/felt experience · preheader extends not repeats · no spam triggers.

**Above the fold:** first content is hero image/headline (no spacer rows) · specifier hero has Pillow-baked text · newsletter uses display-first hero · primary CTA before 2 screens · white wordmark on dark nav · navigator block present for 2+ story newsletters.

**Video:** play button baked in (not CSS) · thumbnail links to correct YouTube URL · no duplicate video references · transition bar doesn't repeat hero.

**Content:** no paragraph >3 lines · scannable structure · primary CTA ≥3 times · phone number ≥1 · offer before booking options · FAQ plain Q/A.

**Images:** all src on `stratus.campaign-image.com` · white wordmark on dark nav/footer · heights adjusted for crop · descriptive alt text · white-bordered images on white/cream.

**Technical:** test-send to self · all images load · all booking links active · Zoho tracking on phone if CallRail active · HTML footer = logo + social only.

---

## 3. Changelog

| Version | Date | Changes |
|---|---|---|
| 3.0 | Apr 2026 | Navigator block, cream body `#F5EFE6`, inline CTA cards, tightened vertical spacing, FAQ plain Q/A rule, no-emoji subject rule, Zoho footer clarification. |
| 2.0 | Apr 2026 | Technical production rules from Ketra build. Newsletter + Specifier blueprints. Pillow hero method, table-based structure. |
| 1.0 | Mar 2026 | Original research framework: subject lines, above the fold, CTAs, voice, benchmarks. |

---

*Maintained by Demand Growth Partner · demandgrowthpartner.com · v3.0*
