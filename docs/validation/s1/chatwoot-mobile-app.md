# chatwoot-mobile-app

mobile app (React Native) — https://github.com/chatwoot/chatwoot-mobile-app @ `e3c8fc5f3d0ece96ea6843e38759bc9b44e13112`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 775 files = 677 covered + 0 partial + 98 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 3.5 s for 83,900 lines |
| Claims | fact 5544, hypothesis 8486; secrets redacted: 7 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for json: 45
- binary: 27
- no analyzer for diff: 8
- no analyzer for markdown: 6
- no analyzer for yaml: 3
- no analyzer for *.aidigestignore: 1
- no analyzer for *.mdc: 1
- no analyzer for *.example: 1
- no analyzer for *.eslintignore: 1
- no analyzer for *.gitignore: 1
- excluded: sensitive (sensitive path): 1
- no analyzer for *.prettierignore: 1
- no analyzer for *.prettierrc: 1
- no analyzer for LICENSE: 1

Partly analysed:
- none

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `imports` | `react` | `src/components-next/common/avatar/AvatarImage.tsx:1-1` | `import React, { useEffect } from 'react';` |
| ok | `imports` | `@/types` | `src/store/conversation-participant/conversationParticipantService.ts:8-8` | `import { Agent } from '@/types';` |
| ok | `imports` | `react-native-reanimated` | `src/screens/inbox/InboxScreen.tsx:3-3` | `import Animated, { SharedValue } from 'react-native-reanimated';` |
| ok | `defines` | `src/types/common/Dashboard.ts::Content` | `src/types/common/Dashboard.ts:7-10` | `interface Content {` |
| ok | `imports` | `react-native-svg` | `src/svg-icons/menu-icons/CannedResponse.tsx:2-2` | `import Svg, { Path } from 'react-native-svg';` |
| ok | `imports` | `./MessageError` | `src/screens/chat-screen/components/message-components/index.ts:14-14` | `export * from './MessageError';` |
| ok | `imports` | `./Mute` | `src/svg-icons/status-icons/index.ts:1-1` | `export * from './Mute';` |
| ok | `imports` | `./settingsTypes` | `src/store/settings/settingsSlice.ts:4-4` | `import { NotificationSettings } from './settingsTypes';` |
| ok | `imports` | `react-native-reanimated` | `src/components-next/common/slider/Slider.stories.tsx:3-3` | `import { useSharedValue } from 'react-native-reanimated';` |
| ok | `imports` | `@/utils` | `src/screens/conversations/components/conversation-filters/InboxFilters.tsx:13-13` | `import { getChannelIcon } from '@/utils';` |
| ok | `defines` | `src/utils/withAnchorPoint.ts::withAnchorPoint` | `src/utils/withAnchorPoint.ts:22-63` | `export const withAnchorPoint = (transform: TransformsStyle, anchorPoint: Point, size: Size` |
| ok | `imports` | `react-native` | `src/hooks/useImageDimensions.ts:2-2` | `import { Image as RNImage } from 'react-native';` |
| ok | `imports` | `@reduxjs/toolkit` | `src/store/macro/macroActions.ts:1-1` | `import { createAsyncThunk } from '@reduxjs/toolkit';` |
| ok | `imports` | `./uk.json` | `src/i18n/index.js:33-33` | `import uk from './uk.json';` |
| ok | `defines` | `src/store/search/searchTypes.ts::SearchMessagesResponse` | `src/store/search/searchTypes.ts:40-42` | `export interface SearchMessagesResponse {` |
| ok | `imports` | `@/store/notification/notificationTypes` | `src/screens/inbox/InboxScreen.tsx:26-26` | `import { InboxSortTypes } from '@/store/notification/notificationTypes';` |
| ok | `defines` | `src/screens/chat-screen/components/message-components/DeliveryStatus.t` | `src/screens/chat-screen/components/message-components/DeliveryStatus.tsx:25-203` | `export const DeliveryStatus = (props: DeliveryStatusProps) => {` |
| ok | `imports` | `@/constants` | `src/screens/chat-screen/components/message-components/MessageError.tsx:8-8` | `import { ORIENTATION } from '@/constants';` |
| ok | `defines` | `src/screens/chat-screen/components/chat-header/ChatHeaderContainer.tsx` | `src/screens/chat-screen/components/chat-header/ChatHeaderContainer.tsx:123-130` | `const handleBackPress = () => {` |
| ok | `imports` | `@/store/search/searchTypes` | `src/screens/search/components/views/AllResultsView.tsx:6-6` | `import type { SearchItem, SearchSectionType } from '@/store/search/searchTypes';` |
| ok | `imports` | `@/store/conversation/conversationSelectedSlice` | `src/navigation/tabs/AppTabs.tsx:42-42` | `import { clearSelection } from '@/store/conversation/conversationSelectedSlice';` |
| ok | `imports` | `react-native` | `src/screens/chat-screen/components/message-item/Message.tsx:42-42` | `import { Dimensions, View, Text } from 'react-native';` |
| ok | `imports` | `@/types` | `src/utils/specs/attachmentUtils.spec.ts:2-2` | `import type { ImageMetadata } from '@/types';` |
| ok | `imports` | `./contactMockData` | `src/store/contact/specs/contactActions.spec.ts:3-3` | `import { mockContactLabelsResponse } from './contactMockData';` |
| ok | `imports` | `react` | `src/utils/navigationUtils.ts:1-1` | `import * as React from 'react';` |
| ok | `defines` | `src/store/conversation/conversationTypes.ts::RetryMessagePayload` | `src/store/conversation/conversationTypes.ts:258-261` | `export interface RetryMessagePayload {` |
| ok | `defines` | `src/svg-icons/common/KeyRound.tsx::KeyRoundIcon` | `src/svg-icons/common/KeyRound.tsx:6-29` | `export const KeyRoundIcon = ({ stroke = '#858585' }: IconProps): JSX.Element => {` |
| ok | `imports` | `@/types` | `src/store/macro/macroTypes.ts:1-1` | `import type { Macro } from '@/types';` |
| ok | `defines` | `src/store/inbox/inboxTypes.ts::InboxResponse` | `src/store/inbox/inboxTypes.ts:3-5` | `export interface InboxResponse {` |
| ok | `imports` | `@/store/team/teamSelectors` | `src/screens/conversations/components/conversation-actions/UpdateTeam.tsx:14-14` | `import { selectLoading } from '@/store/team/teamSelectors';` |
