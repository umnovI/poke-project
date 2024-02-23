import axios from "axios";
import { useQuery } from "react-query";
import ItemsTPL from "./ItemsTPL";

export default function Items({
  itemsPerPage,
  currentPage,
  currentOffset,
  setCurrentPage,
  setOffset,
}) {
  let itemCount = null;
  let totalPages = null;

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
    { retry: false, staleTime: Infinity, refetchOnWindowFocus: false }
  );
  const onPageChange = (page) => {
    console.log("onPageChange has been triggered.");
    setCurrentPage(page);
    console.log("offset: ", page * itemsPerPage - itemsPerPage);
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

  let paginationData = {
    currentPage: currentPage,
    totalPages: totalPages,
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
