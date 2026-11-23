#pragma once
#ifndef _INDUDELETE_SERVICE_
#define _INDUDELETE_SERVICE_

#include <string>
#include <vector>
using namespace std;

/**
 * 行业分类删除服务
 */
class InduDeleteService
{
public:
	// 通过ID批量删除数据
	bool removeData(vector<string>& id);
};

#endif // !_INDUDELETE_SERVICE_
