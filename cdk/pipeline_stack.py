"""
cdk/pipeline_stack.py - AWS CDK Stack
Author: Abraham Agbolosoo

Provisions: CodePipeline, CodeBuild, ECR, Lambda, CodeDeploy, SNS, CloudWatch
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_codebuild as codebuild,
    aws_ecr as ecr,
    aws_lambda as lambda_,
    aws_codedeploy as codedeploy,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_cloudwatch as cloudwatch,
    aws_s3 as s3,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class PythonLambdaPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        github_owner       = "codeagbolosoo"
        github_repo        = "aws-lambda-cicd"
        github_branch      = "main"
        approval_email     = "your@email.com"   # TODO: update
        lambda_memory      = 512
        lambda_timeout     = 30

        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        ecr_repo = ecr.Repository(
            self, "LambdaEcrRepo",
            repository_name="my-python-lambda",
            removal_policy=RemovalPolicy.RETAIN,
            image_scan_on_push=True,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=20)],
        )

        lambda_fn = lambda_.DockerImageFunction(
            self, "PythonLambda",
            function_name="my-python-lambda",
            code=lambda_.DockerImageCode.from_ecr(ecr_repo),
            memory_size=lambda_memory,
            timeout=Duration.seconds(lambda_timeout),
            environment={"STAGE": "prod"},
        )

        staging_alias = lambda_.Alias(
            self, "StagingAlias",
            alias_name="staging",
            version=lambda_fn.current_version,
        )

        prod_alias = lambda_.Alias(
            self, "ProdAlias",
            alias_name="prod",
            version=lambda_fn.current_version,
        )

        codedeploy_app = codedeploy.LambdaApplication(
            self, "CodeDeployApp",
            application_name="my-python-lambda-app",
        )
        codedeploy.LambdaDeploymentGroup(
            self, "ProdDeploymentGroup",
            application=codedeploy_app,
            alias=prod_alias,
            deployment_config=codedeploy.LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,
            deployment_group_name="prod-dg",
        )

        approval_topic = sns.Topic(self, "ApprovalTopic",
                                   display_name="Lambda Pipeline Prod Approval")
        approval_topic.add_subscription(subs.EmailSubscription(approval_email))

        cb_role = iam.Role(
            self, "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        ecr_repo.grant_pull_push(cb_role)
        lambda_fn.grant_invoke(cb_role)
        cb_role.add_to_policy(iam.PolicyStatement(
            actions=["lambda:UpdateFunctionCode", "lambda:PublishVersion",
                     "lambda:UpdateAlias", "lambda:GetAlias"],
            resources=[lambda_fn.function_arn],
        ))

        build_env = codebuild.BuildEnvironment(
            build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
            privileged=True,
            compute_type=codebuild.ComputeType.SMALL,
        )

        test_project = codebuild.PipelineProject(
            self, "TestProject", project_name="python-lambda-test",
            role=cb_role, environment=build_env,
            build_spec=codebuild.BuildSpec.from_source_filename("buildspecs/buildspec-test.yml"),
        )
        build_project = codebuild.PipelineProject(
            self, "BuildProject", project_name="python-lambda-build",
            role=cb_role, environment=build_env,
            environment_variables={"ECR_REPO_URI": codebuild.BuildEnvironmentVariable(value=ecr_repo.repository_uri)},
            build_spec=codebuild.BuildSpec.from_source_filename("buildspecs/buildspec-build.yml"),
        )
        security_project = codebuild.PipelineProject(
            self, "SecurityProject", project_name="python-lambda-security",
            role=cb_role, environment=build_env,
            build_spec=codebuild.BuildSpec.from_source_filename("buildspecs/buildspec-security.yml"),
        )
        staging_deploy = codebuild.PipelineProject(
            self, "StagingDeployProject", project_name="python-lambda-deploy-staging",
            role=cb_role, environment=build_env,
            environment_variables={"FUNCTION_NAME": codebuild.BuildEnvironmentVariable(value=lambda_fn.function_name)},
            build_spec=codebuild.BuildSpec.from_source_filename("buildspecs/buildspec-deploy-staging.yml"),
        )
        prod_deploy = codebuild.PipelineProject(
            self, "ProdDeployProject", project_name="python-lambda-deploy-prod",
            role=cb_role, environment=build_env,
            environment_variables={"FUNCTION_NAME": codebuild.BuildEnvironmentVariable(value=lambda_fn.function_name)},
            build_spec=codebuild.BuildSpec.from_source_filename("buildspecs/buildspec-deploy-prod.yml"),
        )

        cloudwatch.Alarm(
            self, "LambdaErrorAlarm",
            alarm_name="my-lambda-errors",
            metric=lambda_fn.metric_errors(period=Duration.minutes(1)),
            threshold=5, evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        source_artifact = codepipeline.Artifact("SourceArtifact")
        build_artifact  = codepipeline.Artifact("BuildArtifact")

        codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name="python-lambda-pipeline",
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageProps(stage_name="Source", actions=[
                    actions.GitHubSourceAction(
                        action_name="GitHub_Source", owner=github_owner,
                        repo=github_repo, branch=github_branch,
                        oauth_token=cdk.SecretValue.secrets_manager("github-token"),
                        output=source_artifact,
                    )
                ]),
                codepipeline.StageProps(stage_name="Test", actions=[
                    actions.CodeBuildAction(action_name="Run_Tests",
                        project=test_project, input=source_artifact)
                ]),
                codepipeline.StageProps(stage_name="Build", actions=[
                    actions.CodeBuildAction(action_name="Build_Docker_Image",
                        project=build_project, input=source_artifact, outputs=[build_artifact])
                ]),
                codepipeline.StageProps(stage_name="SecurityScan", actions=[
                    actions.CodeBuildAction(action_name="Security_Scan",
                        project=security_project, input=source_artifact)
                ]),
                codepipeline.StageProps(stage_name="DeployStaging", actions=[
                    actions.CodeBuildAction(action_name="Deploy_To_Staging",
                        project=staging_deploy, input=build_artifact)
                ]),
                codepipeline.StageProps(stage_name="ApproveProduction", actions=[
                    actions.ManualApprovalAction(
                        action_name="Approve_Production",
                        notification_topic=approval_topic,
                        additional_information="Review staging smoke tests then approve for prod.",
                    )
                ]),
                codepipeline.StageProps(stage_name="DeployProduction", actions=[
                    actions.CodeBuildAction(action_name="Deploy_To_Production",
                        project=prod_deploy, input=build_artifact)
                ]),
            ],
        )

        cdk.CfnOutput(self, "EcrRepoUri", value=ecr_repo.repository_uri)
        cdk.CfnOutput(self, "LambdaFunctionName", value=lambda_fn.function_name)


app = cdk.App()
PythonLambdaPipelineStack(
    app, "PythonLambdaPipelineStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)
app.synth()
