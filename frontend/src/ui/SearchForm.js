import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";

export default function Component() {
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
            required
          />
          <button
            type="submit"
            className="search-button-blue absolute top-0 end-0 h-full p-2.5"
          >
            <MagnifyingGlassIcon className="w-4 h-4 font-bold" />
            <span className="sr-only">Search</span>
          </button>
        </div>
      </form>
    </>
  );
}
