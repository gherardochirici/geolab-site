# geoLAB website

Static site of geoLAB, Laboratory of Forest Geomatics (University of Florence), online at https://geolabforest.com.

- `content/`: pages in Markdown (projects, news, publications, people, about)
- `static/`: CSS and fixed images
- `build.py`: generates the site into `docs/` (`python build.py`, standard library only)
- `docs/`: generated site (git-ignored, except `docs/media/`, the image store that is edited by hand)
- `.github/workflows/pages.yml`: GitHub Actions builds the site and publishes it on GitHub Pages at every merge into `main`

The site is English only. Do not edit `docs/` by hand, except for images in `docs/media/`: change `content/` or `static/`.

## Contributing

Lab members who want to add or update content: install Git and Python 3, clone this repository, open the folder in Claude Code and follow `CLAUDE.md`, which holds the rules (English only, public facts only, EU funding statement on funded projects) and the workflow (a branch and a pull request, never a direct push to `main`).
