# retail-store-sample-app

microservices (Java, Go, Node) + Terraform + Kubernetes — https://github.com/aws-containers/retail-store-sample-app @ `d7a380b843e0759e58754f74188ea18252a51415`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 716 files = 373 covered + 21 partial + 322 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 4.0 s for 139,658 lines |
| Claims | fact 3762, hypothesis 3854; secrets redacted: 15 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- kubernetes@1.1 failed: TemplatedManifestError: 56
- no analyzer for yaml: 52
- binary: 43
- no analyzer for json: 41
- no analyzer for markdown: 23
- no analyzer for html: 20
- no analyzer for *.gitignore: 10
- no analyzer for *.txt: 7
- no analyzer for gotmpl: 7
- no analyzer for *.helmignore: 6
- no analyzer for *.dockerignore: 6
- too large: 5
- no analyzer for xml: 5
- no analyzer for *.tpl: 5
- no analyzer for *.source: 5
- no analyzer for css: 5
- no analyzer for properties: 4
- no analyzer for *.lock: 4
- no analyzer for mvnw: 3
- no analyzer for batch: 3
- no analyzer for *.prettierrc: 2
- no analyzer for toml: 1
- no analyzer for *.prettierignore: 1
- no analyzer for LICENSE: 1
- no analyzer for Tiltfile: 1
- no analyzer for *.factories: 1
- no analyzer for *.sum: 1
- excluded: sensitive (sensitive path): 1
- no analyzer for *.openapi-generator-ignore: 1
- no analyzer for VERSION: 1
- no analyzer for sql: 1

Partly analysed:
- definitions unverified for bash (Hypotheses): 21
- imports not extracted for bash: 21
- calls not extracted for bash: 21

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `imports` | `org.springframework.web.bind.annotation.RequestMapping` | `src/ui/src/main/java/com/amazon/sample/ui/web/UtilityController.java:40-40` | `import org.springframework.web.bind.annotation.RequestMapping;` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/Check` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/Checkout.java:201-204` | `public ShippingRates getShippingRates() {` |
| ok | `requires` | `package:go/github.com/go-logr/stdr` | `src/catalog/go.mod:45-45` | `github.com/go-logr/stdr v1.2.2 // indirect` |
| ok | `references` | `tf:terraform/eks/default/module.container_images` | `terraform/eks/default/kubernetes.tf:91-91` | `image_repository              = module.container_images.result.catalog.repository` |
| ok | `imports` | `java.util.Map` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/CheckoutRequest.java:8-8` | `import java.util.Map;` |
| ok | `imports` | `jakarta.validation.constraints.Pattern` | `src/ui/src/main/java/com/amazon/sample/ui/web/payload/PaymentDetailsRequest.java:22-22` | `import jakarta.validation.constraints.Pattern;` |
| ok | `imports` | `lombok.Data` | `src/cart/src/main/java/com/amazon/sample/carts/web/api/Item.java:23-23` | `import lombok.Data;` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/client/cart/carts/item/merge` | `src/ui/src/main/java/com/amazon/sample/ui/client/cart/carts/item/merge/MergeRequestBuilder.java:66-75` | `public void get(` |
| ok | `imports` | `com.fasterxml.jackson.annotation.JsonPropertyDescription` | `src/orders/src/main/java/com/amazon/sample/events/orders/OrderCreatedEvent.java:23-23` | `import com.fasterxml.jackson.annotation.JsonPropertyDescription;` |
| ok | `references` | `tf:terraform/lib/ecs/data.aws_iam_policy_document.orders_db_secret` | `terraform/lib/ecs/orders.tf:60-60` | `policy = data.aws_iam_policy_document.orders_db_secret.json` |
| ok | `imports` | `com.microsoft.kiota.RequestInformation` | `src/ui/src/main/java/com/amazon/sample/ui/client/orders/orders/OrdersRequestBuilder.java:9-9` | `import com.microsoft.kiota.RequestInformation;` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/web/payload/CartChangeReques` | `src/ui/src/main/java/com/amazon/sample/ui/web/payload/CartChangeRequest.java:23-29` | `public class CartChangeRequest {` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/services/metadata/providers/` | `src/ui/src/main/java/com/amazon/sample/ui/services/metadata/providers/ResourceMetadataProvider.java:34-53` | `public MetadataSet get() {` |
| ok | `imports` | `../models/CheckoutRequest` | `src/checkout/src/checkout/shipping/MockShippingService.ts:19-19` | `import { CheckoutRequest } from '../models/CheckoutRequest';` |
| ok | `imports` | `org.springframework.ai.chat.model.ChatResponse` | `src/ui/src/main/java/com/amazon/sample/ui/chat/MockChatModel.java:24-24` | `import org.springframework.ai.chat.model.ChatResponse;` |
| ok | `requires` | `package:npm/@nestjs/core` | `src/checkout/package.json:27-27` | `"@nestjs/core": "^11.2.5",` |
| ok | `imports` | `org.springframework.beans.factory.annotation.Value` | `src/ui/src/main/java/com/amazon/sample/ui/web/util/CommonAttributesControllerAdvice.java:23-23` | `import org.springframework.beans.factory.annotation.Value;` |
| ok | `imports` | `fmt` | `src/catalog/main.go:21-21` | `"fmt"` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/client/catalog/models/model/` | `src/ui/src/main/java/com/amazon/sample/ui/client/catalog/models/model/Product.java:72-81` | `public Map<String, java.util.function.Consumer<ParseNode>> getFieldDeserializers() {` |
| ok | `imports` | `node:process` | `src/checkout/src/tracing.ts:5-5` | `import process from 'node:process';` |
| ok | `requires` | `package:npm/@nestjs/schematics` | `src/checkout/package.json:48-48` | `"@nestjs/schematics": "^11.0.5",` |
| ok | `imports` | `com.microsoft.kiota.serialization.Parsable` | `src/ui/src/main/java/com/amazon/sample/ui/client/cart/models/Cart.java:4-4` | `import com.microsoft.kiota.serialization.Parsable;` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/web/CheckoutController.java:` | `src/ui/src/main/java/com/amazon/sample/ui/web/CheckoutController.java:75-113` | `public Mono<String> handleShipping(` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/Check` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/CheckoutSubmitted.java:221-225` | `public void setItems(` |
| ok | `declares` | `tf:terraform/lib/ecs/module.alb_sg` | `terraform/lib/ecs/alb.tf:1-14` | `module "alb_sg" {` |
| ok | `declares` | `tf:terraform/lib/eks/null_resource.addons_blocker` | `terraform/lib/eks/eks.tf:167-172` | `resource "null_resource" "addons_blocker" {` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/Check` | `src/ui/src/main/java/com/amazon/sample/ui/client/checkout/models/CheckoutRequest.java:162-166` | `public void setItems(` |
| ok | `sources` | `source:../../lib/images` | `terraform/eks/default/kubernetes.tf:34-34` | `source = "../../lib/images"` |
| ok | `imports` | `org.springframework.http.codec.ServerSentEvent` | `src/ui/src/main/java/com/amazon/sample/ui/web/ChatController.java:28-28` | `import org.springframework.http.codec.ServerSentEvent;` |
| ok | `defines` | `src/ui/src/main/java/com/amazon/sample/ui/config/StoreServices.java::S` | `src/ui/src/main/java/com/amazon/sample/ui/config/StoreServices.java:57-71` | `public RequestAdapter getRequestAdapter(` |
