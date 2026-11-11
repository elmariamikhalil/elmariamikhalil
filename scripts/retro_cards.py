name: Retro Profile Cards

on:
  schedule:
    - cron: "0 */6 * * *"   # refresh every 6 hours
  workflow_dispatch:        # run it by hand from the Actions tab
  push:
    branches: [main]
    paths:
      - "scripts/retro_cards.py"
      - ".github/workflows/profile-summary-cards.yml"

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install fonttools
      - name: Generate cards
        env:
          GH_TOKEN: ${{ secrets.SUMMARY_GITHUB_TOKEN }}
          USERNAME: ${{ github.repository_owner }}
          DISPLAY_NAME: Khalil Elmariami
          TAGLINE: Full stack web developer
          EMAIL: elmariamikhalil@gmail.com
          TIME_ZONE: Africa/Casablanca
          EXCLUDE_REPOS: keeper,shopify-old,material-kit-react,React-admin
        run: python scripts/retro_cards.py
      - name: Commit cards
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add assets
          git diff --cached --quiet || git commit -m "chore: refresh retro cards"
          git push
