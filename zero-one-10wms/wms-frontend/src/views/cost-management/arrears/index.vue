<script lang="ts" setup>
import ReceiptList from "../components/receipt-list.vue";

definePage({
	meta: {
		menuType: "page",
		text: "欠费管理",
		icon: "IconSetting",
	},
});
</script>

<template>
	<section class="arrears-root">
		<h2>欠费管理</h2>
		<ReceiptList mode="unpaid" />
	</section>
</template>

<style lang="scss" scoped>
.arrears-root {
	width: 100%;
}
</style>
