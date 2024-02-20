import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import axios from "axios";
import { useEffect, useState } from "react";
import { useQuery } from "react-query";

export default function Component({
  setFoundData,
  currentOffset,
  itemsPerPage,
}) {
  const [input, setInput] = useState(null);
  const [query, setQuery] = useState(null);

  console.log("I'm sending:", query);
  const {
    isLoading,
    error,
    data: response,
  } = useQuery(
    `searching-${query + currentOffset}`,
    () =>
      axios(
        `/api/search/pokemon/?q=${query}&offset=${currentOffset}&limit=${itemsPerPage}`
      ),
    { retry: false, enabled: Boolean(query) }
  );

  function handleSearchClick(event) {
    event.preventDefault();
    console.log(event);
    if (input) {
      let value = input.toLowerCase();
      if (query !== value) {
        setQuery(value);
      }
    } else {
      setQuery(null);
    }
  }

  useEffect(() => {
    if (!isLoading && !error && response) {
      setFoundData(response);
    } else if (!response) {
      setFoundData(null);
    }
  }, [isLoading, error, response, query, setFoundData]);

  return (
    <>
      <form className="flex items-center">
        <label htmlFor="search-field" className="sr-only">
          Search
        </label>
        <div className="relative w-full">
          <input
            type="text"
            name="query"
            id="search-field"
            className="input-base w-full ps-4 p-2.5"
            placeholder="Search your pokémon..."
            onChange={(event) => setInput(event.target.value)}
          />
          <button
            className="search-button-blue absolute top-0 end-0 h-full p-2.5"
            onClick={handleSearchClick}
          >
            <MagnifyingGlassIcon className="w-4 h-4 font-bold" />
            <span className="sr-only">Search</span>
          </button>
        </div>
      </form>
    </>
  );
}
