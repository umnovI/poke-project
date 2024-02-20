import ItemsTPL from "./ItemsTPL";

export default function FoundItems({
  searchData,
  itemsPerPage,
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
    setOffset(page * itemsPerPage - itemsPerPage);
  };
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
