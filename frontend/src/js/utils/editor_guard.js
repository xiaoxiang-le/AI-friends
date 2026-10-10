import {onMounted,onBeforeUnmount} from 'vue'
import {onBeforeRouteLeave} from 'vue-router'
export function useEditorGuard(hasChanges) {
  function beforeUnload(event) {if(hasChanges()) {event.preventDefault();event.returnValue=''}}
  onMounted(() => window.addEventListener('beforeunload',beforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload',beforeUnload))
  onBeforeRouteLeave(() => !hasChanges() || window.confirm('改动尚未保存，确定离开吗？'))
}
