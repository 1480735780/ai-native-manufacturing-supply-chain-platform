<script lang="ts" setup>
import NoticeOrderPage from "@/components/notice-order/NoticeOrderPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "客户退货",
		icon: "IconSetting",
	},
});
</script>

<template>
	<NoticeOrderPage title="客户退货" fixed-order-type-code="03" simple hide-complete />
</template>
