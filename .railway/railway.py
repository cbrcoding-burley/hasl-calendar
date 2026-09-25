from railway_sdk import define_railway, github, preserve, project, service, volume


@define_railway
def main(ctx=None):
    data = volume(
        "data",
        {
            "alerts": {"usage": {"100": {}, "80": {}, "95": {}}},
            "allowOnlineResize": True,
            "region": "us-east4-eqdc4a",
            "sizeMB": 5000,
        },
    )
    # Adding a comment so we can see the thing work as god intended
    hasl_calendar_server = service(
        "hasl-calendar-server",
        source=github(
            "cbrcoding-burley/hasl-calendar", checkSuites=True, rootDirectory="/"
        ),
        replicas={"us-east4-eqdc4a": 1},
        deploy={"drainingSeconds": 0, "overlapSeconds": 0},
        volumeMounts={"/data": data},
        env={"DATABASE_URL": preserve(), "SYNC_PUBLIC_KEY": preserve()},
    )

    hasl_calendar_cron = service(
        "hasl-calendar-cron",
        source=github(
            "cbrcoding-burley/hasl-calendar", checkSuites=True, rootDirectory="/src"
        ),
        replicas={"us-east4-eqdc4a": 1},
        deploy={
            "cronSchedule": "*/15 * * * *",
            "drainingSeconds": 0,
            "overlapSeconds": 0,
            "restartPolicyType": "NEVER",
        },
        env={"HASL_CALENDAR_URL": preserve(), "SYNC_PRIVATE_KEY": preserve()},
    )

    return project(
        "hasl-calendar", resources=[hasl_calendar_server, hasl_calendar_cron, data]
    )
