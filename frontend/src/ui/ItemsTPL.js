import { Pagination } from "flowbite-react";

export default function Component({
  isLoading,
  error,
  response,
  itemCount,
  paginationData,
}) {
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
            currentPage={paginationData.currentPage}
            totalPages={paginationData.totalPages}
            onPageChange={paginationData.onPageChange}
          />
        </div>
      )}
    </>
  );
}
