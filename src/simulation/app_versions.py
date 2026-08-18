from datetime import date


class AppVersionResolver:
    def __init__(
        self,
        start_date: date,
        config: dict,
    ):
        self.start_date = start_date
        self.config = config

    def version_for_date(
        self,
        simulation_date: date,
    ) -> str:
        day_number = (
            simulation_date - self.start_date
        ).days + 1

        if day_number < 1:
            raise ValueError(
                "Simulation date cannot be earlier than start date"
            )

        for version_config in self.config["versions"]:
            start_day = int(
                version_config["start_day"]
            )

            end_day = version_config["end_day"]

            if (
                day_number >= start_day
                and (
                    end_day is None
                    or day_number <= int(end_day)
                )
            ):
                return str(
                    version_config["version"]
                )

        raise ValueError(
            f"No app version configured for day {day_number}"
        )

    def engagement_multiplier(
        self,
        version: str,
        platform: str,
        device_tier: str,
    ) -> float:
        regression = self.config["regression"]

        if (
            version == str(regression["version"])
            and platform == regression["platform"]
            and device_tier == regression["device_tier"]
        ):
            return float(
                regression["engagement_multiplier"]
            )

        return 1.0
