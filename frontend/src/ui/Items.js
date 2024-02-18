import axios from "axios";
import { Pagination } from "flowbite-react";
import { useState } from "react";
import { useQuery } from "react-query";

export default function Component({ openedPage }) {
  console.log(openedPage);
  let itemCount = null;
  let totalPages = null;
  const itemsPerPage = 18;
  const [currentPage, setCurrentPage] = useState(
    !openedPage ? 1 : parseInt(openedPage)
  );
  const [currentOffset, setOffset] = useState(
    !openedPage ? 0 : parseInt(openedPage) * itemsPerPage - itemsPerPage
  );

  const {
    isLoading,
    error,
    data: response,
    refetch,
  } = useQuery(
    `pokelist-page-${currentPage}`,
    () =>
      axios(
        `/api/pokemon-detailed/?offset=${currentOffset}&limit=${itemsPerPage}`
      ),
    { retry: false }
  );
  const onPageChange = (page) => {
    console.log("onPageChange has been triggered.");
    setCurrentPage(page);
    console.log("offset: ", page * itemsPerPage - itemsPerPage);
    window.history.replaceState(
      null,
      "", // Historical empty string
      `/?page=${page}`
    );
    document.title = `Pokedex | Page ${page}`;
    setOffset(page * itemsPerPage - itemsPerPage);
    console.log("trigger refetch");
    refetch();
  };

  console.log(response);
  console.log("curPage:", currentPage);
  if (response) {
    itemCount = response.data.count;
    totalPages = Math.ceil(itemCount / itemsPerPage);
  }

  if (currentPage === 1) {
    window.history.replaceState(null, "", "/");
    document.title = "Pokedex";
  }

  return (
    <>
      {isLoading && <div>Fetching data...</div>}
      {error && <div>{error.message}</div>}
      <div className="grid gap-x-8 gap-y-4 grid-cols-3">
        {response &&
          response.data.results.map((pokemon) => (
            <div
              className="bg-neutral-200 rounded-lg shadow-lg p-10"
              key={pokemon.name}
            >
              <div className="grid justify-items-center">
                <div>{pokemon.name}</div>
                <div>
                  <img
                    src={
                      pokemon.sprites.front_default ??
                      "/api/media/?l=empty-url.jpg"
                    }
                    alt={pokemon.name ?? "empty"}
                  />
                </div>
              </div>
            </div>
          ))}
      </div>
      {itemCount && (
        <div className="flex overflow-x-auto sm:justify-center pt-5 pb-10">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </>
  );
}
