from datetime import date


class CampaignResolver:
    def __init__(
        self,
        start_date: date,
        config: dict,
    ):
        self.start_date = start_date
        self.campaigns = config["campaigns"]

    def active_campaigns(
        self,
        simulation_date: date,
    ) -> list[dict]:
        day_number = (
            simulation_date - self.start_date
        ).days + 1

        if day_number < 1:
            raise ValueError(
                "simulation_date cannot be before start_date"
            )

        return [
            campaign
            for campaign in self.campaigns
            if (
                campaign["start_day"]
                <= day_number
                <= campaign["end_day"]
            )
        ]

    def multiplier_for_channel(
        self,
        simulation_date: date,
        channel: str,
    ) -> float:
        multiplier = 1.0

        for campaign in self.active_campaigns(
            simulation_date
        ):
            if campaign["channel"] == channel:
                multiplier *= float(
                    campaign["acquisition_multiplier"]
                )

        return multiplier

    def campaign_id_for_channel(
        self,
        simulation_date: date,
        channel: str,
    ) -> str | None:
        matches = [
            campaign["campaign_id"]
            for campaign in self.active_campaigns(
                simulation_date
            )
            if campaign["channel"] == channel
        ]

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                "Multiple active campaigns for one channel"
            )

        return str(matches[0])
