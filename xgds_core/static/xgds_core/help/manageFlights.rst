{% load static %}
**{{ settings.XGDS_CORE_FLIGHT_MONIKER }}** lets you view and explore all of the {{settings.XGDS_CORE_FLIGHT_MONIKER}}s. A {{settings.XGDS_CORE_FLIGHT_MONIKER}} includes all of the data collected in a single excursion.

Schedule {{ settings.XGDS_CORE_FLIGHT_MONIKER }}s:
------------------------------------------------

 * Go to the *List {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s* page.
 * Check the box to the left of the {{ settings.XGDS_PLANNER_PLAN_MONIKER }} you want to schedule.
 * Click the Schedule Selected blue button on the upper right; this dialog will pop up:

   |schedule_plan_image|

 * Click the box to the right of the When label and select the date AND time (24 hour clock) when you intend to run the {{ settings.XGDS_PLANNER_PLAN_MONIKER }}.  Note it does not have to be exact.
 * Click the Schedule button
 * You will notice that there is now a time in the Scheduled column on the list {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s page.
 * You can schedule the same {{ settings.XGDS_PLANNER_PLAN_MONIKER }} to be run at different times.

Notes: behind the scenes, this created a {{settings.XGDS_CORE_FLIGHT_MONIKER}} for you if there was not already a {{settings.XGDS_CORE_FLIGHT_MONIKER}} for that day.


Manage Schedule:
----------------
In order to start up the video infrastructure on xGDS, you need to start (and stop) {{settings.XGDS_CORE_FLIGHT_MONIKER}}s.  In order to have accurate times in Playbook you need to start (and stop) plans.
 * Go to the *Manage {{settings.XGDS_CORE_FLIGHT_MONIKER}}s* page.
 * You will see a list of the {{settings.XGDS_CORE_FLIGHT_MONIKER}}s, indented under the {{settings.XGDS_CORE_FLIGHT_MONIKER}}s are the {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s scheduled for those {{settings.XGDS_CORE_FLIGHT_MONIKER}}s.
 * If you are just managing {{settings.XGDS_CORE_FLIGHT_MONIKER}}s for today, it is nice to check the *Today* box on the upper left.
 * To start a {{settings.XGDS_CORE_FLIGHT_MONIKER}}, click the start link next to the {{settings.XGDS_CORE_FLIGHT_MONIKER}} you want to start.  Active {{settings.XGDS_CORE_FLIGHT_MONIKER}}s will be listed in green.  You should do this when the rover is up and running and there is a track in xGDS.
 * To start a {{ settings.XGDS_PLANNER_PLAN_MONIKER }}, click the start link next to the {{ settings.XGDS_PLANNER_PLAN_MONIKER }} you want to start.  Active {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s will be listed in green.
 * When the {{ settings.XGDS_PLANNER_PLAN_MONIKER }} is done (aborted or completed) click the stop button next to the {{ settings.XGDS_PLANNER_PLAN_MONIKER }}.  The {{ settings.XGDS_PLANNER_PLAN_MONIKER }} will no longer be green and it will show the stop time.
 * When the {{settings.XGDS_CORE_FLIGHT_MONIKER}} is done, click the stop button next to the {{settings.XGDS_CORE_FLIGHT_MONIKER}}.  The {{settings.XGDS_CORE_FLIGHT_MONIKER}} will no longer be green and it will show the stop time.
 * If you accidentally added {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s you do not intend to run to the {{settings.XGDS_CORE_FLIGHT_MONIKER}}, you can delete them.

Multiple {{settings.XGDS_CORE_FLIGHT_MONIKER}}s on one day:
-----------------------------------------------------------
There may be a time when we have multiple executions on one day, i.e. the rover powers down midday, you move to a different site, or take a lunch break.  There is no limit to how many {{settings.XGDS_CORE_FLIGHT_MONIKER}}s you can set up for one day.  In this case, you will have to manually create all subsequent {{settings.XGDS_CORE_FLIGHT_MONIKER}}s for a day.
Our naming convention for {{settings.XGDS_CORE_FLIGHT_MONIKER}}s is DATELETTER_VEHICLE, for example 20140912A_KRex2.

*To create a {{settings.XGDS_CORE_FLIGHT_MONIKER}} manually:*
 * Go to the *Manage Schedule* page
 * Click the blue Create {{settings.XGDS_CORE_FLIGHT_MONIKER}}s button on the upper right.
 * Choose the date of the {{settings.XGDS_CORE_FLIGHT_MONIKER}} you want to create.
 * Choose the prefix letter of the {{settings.XGDS_CORE_FLIGHT_MONIKER}}; most likely it will be B or higher.  Please use uppercase.
 * Make sure the vehicle(s) you want are checked.
 * Click Create.

*To schedule {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s with one of these hand-created {{settings.XGDS_CORE_FLIGHT_MONIKER}}s, see the steps for Schedule {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s above.*
 * When you are filling out the dialog, choose the {{settings.XGDS_CORE_FLIGHT_MONIKER}} from the drop down (i.e. 20140912B_KRex2).
 * You also must enter the date and time for the {{ settings.XGDS_PLANNER_PLAN_MONIKER }} to execute.
 * Press Schedule.
 * On the Manage Schedule page you will see the {{ settings.XGDS_PLANNER_PLAN_MONIKER }} scheduled under the {{settings.XGDS_CORE_FLIGHT_MONIKER}} you selected.

.. |planner2_index| raw:: html

   <a href="{% url 'planner2_index' %}" target="_blank">List {{ settings.XGDS_PLANNER_PLAN_MONIKER }}s</a>

.. |manage_schedule| raw:: html

   <a href="{% url 'xgds_core_manage' %}" target="_blank">Manage Schedule</a>

.. |schedule_plan_image| image:: {% static 'xgds_planner2/images/SchedulePlan.png' %}
