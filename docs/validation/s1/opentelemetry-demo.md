# opentelemetry-demo

polyglot microservices — https://github.com/open-telemetry/opentelemetry-demo @ `85c2cb253ae3519ef2b3a02984c32614106de5ea`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 612 files = 303 covered + 33 partial + 276 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 6.0 s for 151,218 lines |
| Claims | fact 5034, hypothesis 11335; secrets redacted: 19 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for yaml: 89
- no analyzer for markdown: 34
- no analyzer for json: 26
- binary: 22
- no analyzer for *.dockerignore: 14
- no analyzer for *.in: 6
- no analyzer for jinja2: 6
- no analyzer for *.gitignore: 5
- no analyzer for *.props: 4
- no analyzer for groovy: 4
- no analyzer for properties: 4
- no analyzer for batch: 4
- no analyzer for *.lock: 4
- no analyzer for *.svg: 4
- excluded: sensitive (sensitive path): 3
- no analyzer for toml: 3
- no analyzer for *.sum: 3
- no analyzer for *.csproj: 3
- no analyzer for gradlew: 3
- no analyzer for *.txt: 3
- no analyzer for proto: 2
- no analyzer for *.slnx: 2
- no analyzer for xml: 2
- no analyzer for Gemfile: 2
- no analyzer for css: 2
- no analyzer for po: 2
- no analyzer for *.template: 2
- no analyzer for *.tmpl: 1
- no analyzer for *.gitattributes: 1
- no analyzer for CODEOWNERS: 1
- no analyzer for *.yamlignore: 1
- no analyzer for *.yamllint: 1
- no analyzer for LICENSE: 1
- no analyzer for Makefile: 1
- no analyzer for *.java-version: 1
- no analyzer for *.config: 1
- no analyzer for embeddedtemplate: 1
- no analyzer for heex: 1
- no analyzer for server: 1
- no analyzer for *.eslintrc: 1
- no analyzer for *.prettierignore: 1
- no analyzer for *.prettierrc: 1
- no analyzer for ini: 1
- no analyzer for sql: 1
- no analyzer for *.ruby-version: 1

Partly analysed:
- definitions not extracted for c: 9
- definitions unverified for rust (Hypotheses): 7
- definitions unverified for php (Hypotheses): 6
- definitions not extracted for cpp: 5
- definitions not extracted for kotlin: 3
- definitions unverified for bash (Hypotheses): 2
- imports not extracted for bash: 2
- calls not extracted for bash: 2
- definitions unverified for ruby (Hypotheses): 1

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `requires` | `package:pypi/blinker` | `src/load-generator/requirements.txt:11-11` | `blinker==1.9.0 \` |
| ok | `imports` | `@tanstack/react-query` | `src/frontend/components/CartItems/CartItems.tsx:5-5` | `import { useQuery, UseQueryOptions } from '@tanstack/react-query';` |
| ok | `defines` | `src/frontend/protos/demo.ts::decode~6` | `src/frontend/protos/demo.ts:679-702` | `decode(input: BinaryReader / Uint8Array, length?: number): Empty {` |
| ok | `imports` | `io.opentelemetry.api.common.Attributes` | `src/recommendation/src/main/java/oteldemo/recommendation/RecommendationService.java:12-12` | `import io.opentelemetry.api.common.Attributes;` |
| ok | `requires` | `package:pypi/opentelemetry-instrumentation-replicate` | `src/agent/requirements.txt:2067-2067` | `opentelemetry-instrumentation-replicate==0.62.4 \` |
| ok | `imports` | `iostream` | `src/currency/src/tracer_common.h:19-19` | `#include <iostream>` |
| ok | `defines` | `src/react-native-app/protos/demo.ts::encode~29` | `src/react-native-app/protos/demo.ts:2403-2408` | `encode(message: PlaceOrderResponse, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer ` |
| ok | `imports` | `io.opentelemetry.api.OpenTelemetry` | `src/recommendation/src/main/java/oteldemo/recommendation/GrpcTelemetryConfiguration.java:10-10` | `import io.opentelemetry.api.OpenTelemetry;` |
| ok | `based_on` | `image:gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853` | `src/checkout/Dockerfile:24-24` | `FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7ee` |
| ok | `defines` | `src/frontend/protos/demo.ts::UpdateFlagResponse` | `src/frontend/protos/demo.ts:240-241` | `export interface UpdateFlagResponse {` |
| ok | `defines` | `src/frontend/protos/demo.ts::GetCartRequest` | `src/frontend/protos/demo.ts:38-40` | `export interface GetCartRequest {` |
| ok | `defines` | `src/react-native-app/protos/demo.ts::toJSON~4` | `src/react-native-app/protos/demo.ts:504-510` | `toJSON(message: GetCartRequest): unknown {` |
| ok | `requires` | `package:go/github.com/hashicorp/go-immutable-radix` | `src/checkout/go.mod:44-44` | `github.com/hashicorp/go-immutable-radix v1.3.1 // indirect` |
| ok | `imports` | `limits` | `src/currency/build/generated/proto/grpc/health/v1/health.pb.h:9-9` | `#include <limits>` |
| ok | `imports` | `github.com/open-feature/go-sdk/openfeature` | `src/product-catalog/flags/flags_gen.go:11-11` | `"github.com/open-feature/go-sdk/openfeature"` |
| ok | `defines` | `src/accounting/Helpers.cs::Helpers` | `src/accounting/Helpers.cs:8-33` | `internal static class Helpers` |
| ok | `defines` | `src/flagd-ui/lib/flagd_ui_web.ex::FlagdUiWeb.channel` | `src/flagd-ui/lib/flagd_ui_web.ex:36-40` | `def channel do` |
| ok | `defines` | `src/frontend/protos/demo.ts::decode` | `src/frontend/protos/demo.ts:272-311` | `decode(input: BinaryReader / Uint8Array, length?: number): CartItem {` |
| ok | `imports` | `go.opentelemetry.io/otel/trace` | `src/product-catalog/main.go:36-36` | `"go.opentelemetry.io/otel/trace"` |
| ok | `requires` | `package:npm/typescript` | `src/frontend/package.json:66-66` | `"typescript": "6.0.3"` |
| ok | `imports` | `dev.openfeature.contrib.providers.flagd.FlagdOptions` | `src/recommendation/src/main/java/oteldemo/recommendation/FeatureFlagConfiguration.java:9-9` | `import dev.openfeature.contrib.providers.flagd.FlagdOptions;` |
| ok | `defines` | `src/flagd-ui/lib/flagd_ui/scheduler.ex::FlagdUi.Scheduler.plan_activat` | `src/flagd-ui/lib/flagd_ui/scheduler.ex:311-331` | `defp plan_activations(flags, wanted, config, rand) do` |
| ok | `imports` | `demo.grpc.pb.h` | `src/currency/src/server.cpp:12-12` | `#include <demo.grpc.pb.h>` |
| ok | `based_on` | `image:gcr.io/distroless/java17-debian12:nonroot@sha256:06484c2a9dcc907` | `src/fraud-detection/Dockerfile:16-16` | `FROM gcr.io/distroless/java17-debian12:nonroot@sha256:06484c2a9dcc9070aeafbc0fe752cb9f73bc` |
| ok | `defines` | `src/product-catalog/genproto/oteldemo/demo_grpc.pb.go::testEmbeddedByV` | `src/product-catalog/genproto/oteldemo/demo_grpc.pb.go:1293-1293` | `func (UnimplementedFeatureFlagServiceServer) testEmbeddedByValue()                        ` |
| ok | `imports` | `../../utils/telemetry/InstrumentationMiddleware` | `src/frontend/pages/api/recommendations.ts:5-5` | `import InstrumentationMiddleware from '../../utils/telemetry/InstrumentationMiddleware';` |
| ok | `defines` | `src/ad/src/main/java/oteldemo/problempattern/GarbageCollectionTrigger.` | `src/ad/src/main/java/oteldemo/problempattern/GarbageCollectionTrigger.java:67-79` | `private class Entry {` |
| ok | `requires` | `package:pypi/cffi` | `src/mcp/requirements.txt:233-233` | `cffi==2.1.1 \` |
| ok | `depends_on` | `service:kafka` | `compose.full.yaml:80-80` | `kafka:` |
| ok | `defines` | `src/product-catalog/genproto/oteldemo/demo.pb.go::GetNanos` | `src/product-catalog/genproto/oteldemo/demo.pb.go:1007-1012` | `func (x *Money) GetNanos() int32 {` |
