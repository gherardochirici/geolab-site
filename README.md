# geoLAB website

Static site of geoLAB, Laboratory of Forest Geomatics (University of Florence).

- `content/`: pages in Markdown (projects, news, publications, people, about)
- `static/`: CSS and images
- `build.py`: generates the site into `docs/` (`python build.py`, standard library only)
- `docs/`: generated site, served by GitHub Pages

Do not edit `docs/` by hand: change `content/` or `static/` and rebuild.
