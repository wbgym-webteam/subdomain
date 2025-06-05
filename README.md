# Subdomain for _wbgym.de_

This is the repository, where the Weinberg Secondary School develops a subdomain for their website wbgym.de. It has multiple modules, which are all listen below. The Techstack used here is Python Flask for the backend, SQLite3 for the db and for the frontend plain HTML, CSS and JS.

## Modules

- **TdW** _(v1 Done)_: The module for the "Tag der Wissenschaften" (Day of Science). On this day some experts and grads are coming to the school and talk about a specific topic. The module here is for the students to select their presentation wishes.
- **SmS** _(Planning)_: The module for the "Schüler machen Schule" (Student teaches School). Here students can offer courses for other students, so it is another module for selection of courses. The specific format is yet to be determined.

## Documentation

Before the main page [wbgym.de](https://wbgym.de) switched to Wordpress as a CMS, there was Contao to manage the content and also these modules. The big issue here was the fact that there was no documentation at all. So the main goal of this rewrite is to document everything, so that the next generation of the webteam can easily understand and maintain the code.

The documentation is found in the `/docs` folder. It is written in Markdown and is generated with MkDocs. The documentation is hosted on [GitHub Pages](https://wbgym.github.io/subdomain/).

On these pages you will find all the information you need 💻.
