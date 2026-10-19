# terraform-aws-eks-blueprints

infrastructure as code only — https://github.com/aws-ia/terraform-aws-eks-blueprints @ `fc40e64615785b3dc4db88e57c45a6687ca026b5`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 393 files = 211 covered + 11 partial + 171 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 1.4 s for 22,549 lines |
| Claims | fact 1139, hypothesis 73; secrets redacted: 3 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for markdown: 90
- no analyzer for yaml: 25
- binary: 20
- kubernetes@1.1 failed: TemplatedManifestError: 12
- no analyzer for *.gitignore: 4
- no analyzer for *.helmignore: 4
- no analyzer for *.pages: 3
- excluded: sensitive (sensitive path): 3
- no analyzer for *.txt: 2
- no analyzer for *.drawio: 2
- no analyzer for *.svg: 2
- no analyzer for CODEOWNERS: 1
- no analyzer for json: 1
- no analyzer for LICENSE: 1
- no analyzer for *.example: 1

Partly analysed:
- definitions unverified for bash (Hypotheses): 10
- imports not extracted for bash: 10
- calls not extracted for bash: 10
- Terraform syntax errors: some blocks may be missing or cut: 1

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `sources` | `source:terraform-aws-modules/eks/aws` | `patterns/vpc-lattice/cross-cluster-pod-communication/cluster/eks.tf:6-6` | `source  = "terraform-aws-modules/eks/aws"` |
| ok | `references` | `tf:patterns/ecr-pull-through-cache/module.eks` | `patterns/ecr-pull-through-cache/eks.tf:94-94` | `provider_arn               = module.eks.oidc_provider_arn` |
| ok | `declares` | `tf:patterns/fargate-serverless/provider.kubernetes` | `patterns/fargate-serverless/main.tf:5-15` | `provider "kubernetes" {` |
| ok | `references` | `tf:patterns/vpc-lattice/cross-cluster-pod-communication/environment/aw` | `patterns/vpc-lattice/cross-cluster-pod-communication/environment/main.tf:68-68` | `role       = aws_iam_role.vpc_lattice_role.name` |
| ok | `references` | `tf:patterns/tls-with-aws-pca-issuer/aws_acmpca_certificate_authority.t` | `patterns/tls-with-aws-pca-issuer/main.tf:151-151` | `certificate_authority_arn   = aws_acmpca_certificate_authority.this.arn` |
| ok | `references` | `tf:patterns/gitops/getting-started-argocd/module.eks` | `patterns/gitops/getting-started-argocd/main.tf:30-30` | `host                   = module.eks.cluster_endpoint` |
| ok | `declares` | `tf:patterns/blue-green-upgrade/eks-blue/provider.aws` | `patterns/blue-green-upgrade/eks-blue/main.tf:1-3` | `provider "aws" {` |
| ok | `sources` | `source:terraform-aws-modules/alb/aws` | `patterns/privatelink-access/privatelink.tf:6-6` | `source  = "terraform-aws-modules/alb/aws"` |
| ok | `declares` | `tf:docs/v4-to-v5/example/module.vpc` | `docs/v4-to-v5/example/main.tf:25-48` | `module "vpc" {` |
| ok | `references` | `tf:patterns/blue-green-upgrade/modules/eks_cluster/data.aws_iam_role.e` | `patterns/blue-green-upgrade/modules/eks_cluster/main.tf:276-276` | `try(data.aws_iam_role.eks_admin_role_name[0].arn, data.aws_caller_identity.current.arn),` |
| ok | `references` | `tf:patterns/sso-iam-identity-center/aws_identitystore_user.user` | `patterns/sso-iam-identity-center/sso.tf:144-144` | `member_id         = aws_identitystore_user.user[each.key].user_id` |
| ok | `declares` | `tf:patterns/aws-neuron-efa/module.vpc` | `patterns/aws-neuron-efa/main.tf:86-109` | `module "vpc" {` |
| ok | `declares` | `k8s:GameServer/xonotic` | `patterns/agones-game-controller/test/xonotic/gameserver.yaml:1-13` | `name: "xonotic"` |
| ok | `sources` | `source:terraform-aws-modules/vpc/aws//modules/vpc-endpoints` | `patterns/fully-private-cluster/main.tf:86-86` | `source  = "terraform-aws-modules/vpc/aws//modules/vpc-endpoints"` |
| ok | `references` | `tf:patterns/ml-container-cache/data.aws_ssm_parameter.snapshot_id` | `patterns/ml-container-cache/eks.tf:86-86` | `snapshot_id = nonsensitive(data.aws_ssm_parameter.snapshot_id.value)` |
| ok | `declares` | `tf:patterns/istio/module.eks` | `patterns/istio/main.tf:59-112` | `module "eks" {` |
| ok | `declares` | `tf:patterns/privatelink-access/aws_iam_policy.eks_full_access_policy` | `patterns/privatelink-access/client.tf:75-93` | `resource "aws_iam_policy" "eks_full_access_policy" {` |
| ok | `declares` | `tf:patterns/gitops/multi-cluster-hub-spoke-argocd/spokes/provider.kube` | `patterns/gitops/multi-cluster-hub-spoke-argocd/spokes/main.tf:27-38` | `provider "kubernetes" {` |
| ok | `references` | `tf:patterns/bottlerocket/module.eks_blueprints_addons` | `patterns/bottlerocket/eks.tf:107-107` | `module.eks_blueprints_addons.karpenter.iam_role_arn` |
| ok | `references` | `tf:patterns/private-public-ingress/module.eks` | `patterns/private-public-ingress/main.tf:188-188` | `cluster_name      = module.eks.cluster_name` |
| ok | `sources` | `source:terraform-aws-modules/s3-bucket/aws` | `patterns/stateful/main.tf:342-342` | `source  = "terraform-aws-modules/s3-bucket/aws"` |
| ok | `references` | `tf:patterns/sso-iam-identity-center/module.eks` | `patterns/sso-iam-identity-center/teams.tf:30-30` | `cluster_arn       = module.eks.cluster_arn` |
| ok | `has_labels` | `label:app.kubernetes.io/name=game-2048` | `patterns/gitops/getting-started-argocd/k8s/game-2048.yaml:20-20` | `app.kubernetes.io/name: game-2048` |
| ok | `declares` | `tf:patterns/gitops/multi-cluster-hub-spoke-argocd/spokes/provider.aws` | `patterns/gitops/multi-cluster-hub-spoke-argocd/spokes/main.tf:1-3` | `provider "aws" {` |
| ok | `declares` | `k8s:stars/Service/frontend` | `patterns/aws-vpc-cni-network-policy/charts/demo-application/templates/frontend-svc.yaml:1-11` | `name: frontend` |
| ok | `references` | `tf:patterns/sso-iam-identity-center/aws_ssoadmin_account_assignment.op` | `patterns/sso-iam-identity-center/teams.tf:11-11` | `aws_ssoadmin_account_assignment.operators,` |
| ok | `references` | `tf:patterns/ecr-pull-through-cache/module.vpc` | `patterns/ecr-pull-through-cache/eks.tf:34-34` | `vpc_id     = module.vpc.vpc_id` |
| ok | `declares` | `tf:patterns/kubecost/data.aws_iam_policy_document.cur_bucket_policy` | `patterns/kubecost/main.tf:160-191` | `data "aws_iam_policy_document" "cur_bucket_policy" {` |
| ok | `sources` | `source:terraform-aws-modules/vpc/aws` | `patterns/ml-capacity-block/main.tf:80-80` | `source  = "terraform-aws-modules/vpc/aws"` |
| ok | `declares` | `tf:patterns/sso-okta/okta_group.developers` | `patterns/sso-okta/okta.tf:44-47` | `resource "okta_group" "developers" {` |
