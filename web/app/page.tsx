import { Dashboard } from "@/components/Dashboard";
import { getPageData } from "@/lib/page-data";

/** Server component: fetches the small JSON once a day and hands it to the interactive page. */
export default async function Home() {
  const data = await getPageData();
  return <Dashboard data={data} />;
}
