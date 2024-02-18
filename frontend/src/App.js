import { QueryClient, QueryClientProvider } from "react-query";
import LeftFilter from "./ui/Filters/Left/Filter";
import SortingOrder from "./ui/Filters/Top/SortingOrder";
import Items from "./ui/Items";
import SearchForm from "./ui/SearchForm";

export default function App() {
  const queryClient = new QueryClient();
  const queryString = window.location.search;
  const urlParams = new URLSearchParams(queryString);
  const openedPage = urlParams.get("page") ? urlParams.get("page") : null;
  console.log(queryString);
  console.log(urlParams.get("page"));

  return (
    <div className="container-body md:container md:mx-auto pt-16 px-3">
      <SearchForm />

      <div className="grid grid-cols-auto-1">
        <div></div>
        <div className="my-8 grid grid-cols-2">
          <SortingOrder />
        </div>
        <div className="mr-10">
          <LeftFilter />
        </div>
        <div>
          {/* Caching wrapper */}
          <QueryClientProvider client={queryClient}>
            <Items openedPage={openedPage} />
          </QueryClientProvider>
        </div>
      </div>
    </div>
  );
}
