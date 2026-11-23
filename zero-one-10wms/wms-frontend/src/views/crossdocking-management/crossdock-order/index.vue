<script lang="ts" setup>
import NoticeOrderPage from "@/components/notice-order/NoticeOrderPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "越库订单",
		icon: "IconSetting",
	},
});
</script>

<template>
	<NoticeOrderPage title="越库订单" fixed-order-type-code="04" />
</template>
