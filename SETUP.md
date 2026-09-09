# efkay GitHub profile README — neofetch layout

This version deliberately mirrors the information density and visual grammar of
Andrew6rant's profile card while using efkay-specific content and a custom DNA ASCII.

## Content

- OS / role / location / education / IDE
- three compact stack rows
- hobbies section
- contact section
- GitHub stats section
- portfolio links to `efkay.vercel.app`

## Dynamic GitHub stats

The included Action updates:

- owned repositories
- repositories contributed to
- stars received
- commit contributions
- followers
- authored additions / deletions / net lines of code

The LOC routine caches each repo using its default-branch HEAD SHA, so unchanged
repositories do not need their entire commit history queried again.

## Install

Use your public profile repository:

`fkpanni/fkpanni`

Copy these files into it, then:

```bash
git add .
git commit -m "feat: add neofetch profile readme"
git push
```

The first Action run will replace the preview stat placeholders with live values.

## Edit later

- profile text: `profile.json`
- ASCII: `ascii/helix.txt`

Then run:

```bash
python generate_profile.py
```

or let the included GitHub Action regenerate it.
