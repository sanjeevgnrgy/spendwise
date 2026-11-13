import { Card, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

interface PlaceholderPageProps {
  title: string
  description: string
}

// A page that isn't built yet. Props make it reusable: each placeholder passes its own text.
export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
