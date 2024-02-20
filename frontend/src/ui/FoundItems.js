import ItemsTPL from "./ItemsTPL";

export default function FoundItems({
  searchData,
  itemsPerPage,
  searchQuery,
  setCurrentPage,
  currentPage,
  setOffset,
}) {
  const isLoading = false;
  const error = false;
  const response = searchData;
  const itemCount = searchData.data.count;

  const onPageChange = (page) => {
    console.log("onPageChange has been triggered.");
    setCurrentPage(page);
    window.history.replaceState(
      null,
      "", // Historical empty string
      `/?search=${searchQuery}&page=${page}`
    );
    document.title = `Pokedex | Page ${page}`;
    setOffset(page * itemsPerPage - itemsPerPage);
  };
  if (searchQuery && (currentPage === 1 || !currentPage)) {
    window.history.replaceState(
      null,
      "", // Historical empty string
      `/?search=${searchQuery}`
    );
  }
  const paginationData = {
    currentPage: currentPage,
    totalPages: Math.ceil(itemCount / itemsPerPage),
    onPageChange: onPageChange,
  };

  return (
    <ItemsTPL
      isLoading={isLoading}
      error={error}
      response={response}
      itemCount={itemCount}
      paginationData={paginationData}
    />
  );
}
