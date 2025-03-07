# TdW - Module

This module is for an event called "Tag der Wissenschaften" (Day of Science) at the Weinberg Secondary School.

## Structure

The Login is happening at `auth.py`, where you can choose to login either to the TdW or the [SmS](sms.md) Module. When the students logged in successfully, they will be redirected to `/tdw`. This is where the presentation selection process happens.

There the students can select mulitple presentations from a list of the available ones which are for his grade. When ready, the student submits the selected presentations and afterwards he can logout.

The administration of the TdW module is done in the admin panel. There you can import the presentations and student lists from an `.xlsx`-file. The admin panel automatically creates the necessary database entries and generates the logincodes for the students. The logincodes can be exported to a zip file which contains a `.docx`-file for each class. When you have done all the necessary preperation, you can now activate the module for the students.

**List of auth & admin files**:

- `auth.py`
- `admin_views.py`

_Templates:_

- `login.html`
- `/admin/`

_The models for the DB are found in `models.py`._

**List of module files**:

- `tdw_views.py`
- `tdw_filehandler.py`
- `tdw_logincode_export.py`

_The templates are found in `/templates/tdw/`._
