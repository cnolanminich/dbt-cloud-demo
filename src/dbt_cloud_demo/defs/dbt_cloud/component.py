"""dbt Cloud observability component with demo mode support.

This component loads dbt Cloud asset specifications for observability,
allowing you to view your dbt Cloud assets in the Dagster Asset Graph
and double click into run/materialization history.
"""

import dagster as dg
from dagster_dbt import (
    DbtCloudCredentials,
    DbtCloudWorkspace,
    build_dbt_cloud_polling_sensor,
    load_dbt_cloud_asset_specs,
)


class DbtCloudObservabilityComponent(dg.Component, dg.Model, dg.Resolvable):
    """Component for dbt Cloud observability.

    In real mode, this component:
    - Loads asset specifications from dbt Cloud
    - Creates external assets representing dbt Cloud models
    - Provides a polling sensor to sync run history
    """

    account_id: int
    access_url: str = "https://cloud.getdbt.com"
    token: str = ""
    project_id: int
    environment_id: int

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build real dbt Cloud observability definitions."""
        # Validate required parameters
        required_params = {
            "account_id": self.account_id,
            "token": self.token,
            "project_id": self.project_id,
            "environment_id": self.environment_id
        }
        missing = [k for k, v in required_params.items() if not v]
        if missing:
            raise ValueError(f"Missing required parameters for real mode: {missing}")

        # Create credentials and workspace
        credentials = DbtCloudCredentials(
            account_id=int(self.account_id),
            token=dg.EnvVar("DBT_CLOUD_TOKEN") if self.token == "${DBT_CLOUD_TOKEN}" else self.token,
            access_url=self.access_url
        )

        workspace = DbtCloudWorkspace(
            credentials=credentials,
            project_id=int(self.project_id),
            environment_id=int(self.environment_id)
        )

        # Load asset specs from dbt Cloud
        asset_specs = load_dbt_cloud_asset_specs(workspace=workspace)

        # Build polling sensor
        dbt_cloud_sensor = build_dbt_cloud_polling_sensor(
            workspace=workspace,
        )

        return dg.Definitions(
            assets=asset_specs,
            sensors=[dbt_cloud_sensor]
        )
    
"""dbt Cloud orchestration component with demo mode support.

This component uses Dagster to schedule runs/materializations of your dbt Cloud
assets, either on a cron schedule or based on upstream dependencies.
"""

import dagster as dg
from dagster import AssetExecutionContext
from dagster_dbt import (
    DbtCloudCredentials,
    DbtCloudWorkspace,
    build_dbt_cloud_polling_sensor,
    dbt_cloud_assets,
)


class DbtCloudOrchestrationComponent(dg.Component, dg.Model, dg.Resolvable):
    """Component for dbt Cloud orchestration.

    In real mode, this component:
    - Creates materializable dbt Cloud assets
    - Triggers dbt Cloud jobs from Dagster
    - Applies automation conditions for scheduling
    - Provides a polling sensor to monitor job execution

    """

    account_id: int
    access_url: str = "https://cloud.getdbt.com"
    token: str = ""
    project_id: int
    environment_id: int

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build real dbt Cloud orchestration definitions."""

        # Create credentials and workspace
        credentials = DbtCloudCredentials(
            account_id=int(self.account_id),
            token=dg.EnvVar("DBT_CLOUD_TOKEN") if self.token == "${DBT_CLOUD_TOKEN}" else self.token,
            access_url=self.access_url
        )

        workspace = DbtCloudWorkspace(
            credentials=credentials,
            project_id=int(self.project_id),
            environment_id=int(self.environment_id)
        )

        # Create dbt Cloud assets that can be materialized
        @dbt_cloud_assets(
            workspace=workspace,
            name="dbt_cloud_orchestrated_assets",
        )
        def dbt_cloud_orchestrated_assets(context: dg.AssetExecutionContext, dbt_cloud: DbtCloudWorkspace):
            """Materializable dbt Cloud assets triggered by Dagster."""
            yield from dbt_cloud.cli(args=["build"], context=context).wait()

        # Build polling sensor to monitor job execution
        dbt_cloud_sensor = build_dbt_cloud_polling_sensor(
            workspace=workspace,
        )

        return dg.Definitions(
            assets=[dbt_cloud_orchestrated_assets],
            resources={"dbt_cloud": workspace},
            sensors=[dbt_cloud_sensor]
        )
