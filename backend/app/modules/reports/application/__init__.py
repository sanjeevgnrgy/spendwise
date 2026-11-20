"""The reports module's use case (application/): MonthlyReports, which reads a person's expenses through the bus, has
the monthly-report skill's script work the figures out (D209), and writes the downloads. Not a bus handler: the script
runs with no database session open. The composition root builds it through module.py.
"""
