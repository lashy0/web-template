import { toast } from '@web-app/ui/components/toast'

export default function useCustomToast() {
  return {
    showErrorToast: (title: string, description?: string) =>
      toast.add({ description, title, type: 'error' }),
    showSuccessToast: (title: string, description?: string) =>
      toast.add({ description, title, type: 'success' }),
  }
}
