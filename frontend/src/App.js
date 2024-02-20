import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "react-query";
import LeftFilter from "./ui/Filters/Left/Filter";
import SortingOrder from "./ui/Filters/Top/SortingOrder";
import FoundItems from "./ui/FoundItems";
import Items from "./ui/Items";
import SearchForm from "./ui/SearchForm";

export default function App() {
  const queryClientItems = new QueryClient();
  const queryClientSearch = new QueryClient();

  const queryString = window.location.search;
  const urlParams = new URLSearchParams(queryString);
  const openedPage = urlParams.get("page") ? urlParams.get("page") : null;
  const openedQuery = urlParams.get("search") ? urlParams.get("search") : null;
  const [searchQuery, setSearchQuery] = useState(null);
  const [foundData, setFoundData] = useState(null);
  const itemsPerPage = 18;
  const [currentPage, setCurrentPage] = useState(
    !openedPage ? 1 : parseInt(openedPage)
  );
  const [currentOffset, setOffset] = useState(
    !openedPage ? 0 : parseInt(openedPage) * itemsPerPage - itemsPerPage
  );
  console.log("Found data:", foundData);
  useEffect(() => {
    setSearchQuery(openedQuery);
  }, [openedQuery]);

  return (
    <div className="container-body md:container md:mx-auto pt-16 px-3">
      <QueryClientProvider client={queryClientSearch}>
        <SearchForm
          setFoundData={setFoundData}
          setSearchQuery={setSearchQuery}
          itemsPerPage={itemsPerPage}
          currentOffset={currentOffset}
          searchQuery={searchQuery}
        />
      </QueryClientProvider>

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
          {foundData ? (
            foundData.data.count === 0 ? (
              <div>Nothing was found</div>
            ) : (
              <>
                <FoundItems
                  searchData={foundData}
                  openedPage={openedPage}
                  itemsPerPage={itemsPerPage}
                  searchQuery={searchQuery}
                  currentPage={currentPage}
                  setCurrentPage={setCurrentPage}
                  setOffset={setOffset}
                />
              </>
            )
          ) : (
            <QueryClientProvider client={queryClientItems}>
              <Items
                itemsPerPage={itemsPerPage}
                currentOffset={currentOffset}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                setOffset={setOffset}
              />
            </QueryClientProvider>
          )}
        </div>
      </div>
    </div>
  );
}
