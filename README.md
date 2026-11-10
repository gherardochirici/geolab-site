# geoLAB website

Static site of geoLAB, Laboratory of Forest Geomatics (University of Florence), online at https://geolabforest.com.

- `content/`: pages in Markdown (projects, news, publications, people, about)
- `static/`: CSS and fixed images
- `build.py`: generates the site into `docs/` (`python build.py`, standard library only)
- `docs/`: generated site, served by GitHub Pages (only `docs/media/` is edited by hand)

The site is English only. Do not edit `docs/` by hand, except for images in `docs/media/`: change `content/` or `static/` and rebuild.

## Contributing

Lab members who want to add or update content: install Git and Python 3, clone this repository, open the folder in Claude Code and follow `CLAUDE.md`, which holds the rules (English only, public facts only, EU funding statement on funded projects) and the workflow (a branch and a pull request, never a direct push to `main`).
